import re
import os
import sys
import subprocess
import binascii
from datetime import datetime

import pymongo
import bson.json_util
from bson.objectid import ObjectId

RECORDING_LENGTH = 600
RECORDING_SEGMENT_LENGTH = 60

def exit_with_error(msg, code=1):
    sys.stderr.write(msg + '\n')
    sys.exit(code)

def ssh_runner(host, port, user, keyfile):
    def ssh_cmd(cmd):
        return run_cmd([
            'ssh',
            '-i', keyfile,
            '-p', port,
            '-l', user, host,
            ' '.join(cmd) if isinstance(cmd, (list, tuple)) else cmd,
        ])
    return ssh_cmd


def run_cmd(cmd):
    try:
        proc = subprocess.Popen(cmd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc_comm = proc.communicate()
        if proc.returncode:
            exit_with_error(proc_comm[1].strip().decode('utf8'))
        return [c.strip().decode('utf8') for c in proc_comm]
    except subprocess.TimeoutExpired:
        return


def create_fake_video_segment_file(
        cmd_runner, start, end, stream, offset, size,
        ufvlib_path, ufv_user, camera_uuid):
    start = datetime.utcfromtimestamp(start / 1000)
    end = datetime.utcfromtimestamp(end / 1000)
    video_path = os.path.join(ufvlib_path, 'data', 'videos', camera_uuid)
    dirpath = os.path.join(
        video_path,
        str(start.year),
        *['{:02}'.format(n) for n in start.timetuple()[1:3]])
    filename = '{start}_{end}_{streamid}_{offset}.mp4'.format(
        start=int(start.timestamp() * 1000),
        end=int(end.timestamp() * 1000),
        streamid=stream,
        offset=offset)
    cmd_runner(' && '.join([
        'mkdir -p {}'.format(dirpath),
        'chown -R {} {}'.format(ufv_user, video_path),
        'dd if=/dev/zero of={filename} bs=1 count={size}'.format(
            filename=os.path.join(dirpath, filename),
            size=size)]))


def fake_events(count, camera, recordings_path):
    now = datetime.now()
    counter = 0
    while count:
        start_time = int(now.timestamp()) - (counter * RECORDING_LENGTH)
        event = {
            '_id': ObjectId(
                '{:08x}{}{:06x}'.format(
                    start_time,
                    binascii.hexlify(b'blahs').decode('ascii'),
                    counter)),
            'eventType': 'fullTimeRecording',
            'startTime': start_time,
            'endTime': int(now.timestamp()) - (counter * RECORDING_LENGTH) \
                - RECORDING_LENGTH,
            'cameras': [camera['_id']],
            'locked': False,
            'inProgress': False,
            'markedForDeletion': False,
            'meta': {
                'cameraName': camera['name'],
                'key': 'Ksn9h03',
                'recordingPathId': recordings_path['_id'],
            }
        }
        event['startTime'] *= 1000
        event['endTime'] *= 1000
        count -= 1
        counter += 1
        yield event


def fake_video_segments(event, camera, recordings_path):
    event_time = event['_id'].generation_time.timestamp()
    stream_id = int(event_time - (event_time % (3600 * 12)) * 1000)
    for i in range(int(RECORDING_LENGTH / RECORDING_SEGMENT_LENGTH)):

        # segment.size, segment.streamClockOffset, and segment.streamId
        # are all set to non-sensical values. Doesn't seem to make a difference.
        segment = {
            'cameraId': event['cameras'][0],
            'recordingPathId': recordings_path['_id'],
            'startTime': event['startTime'] \
                + (RECORDING_SEGMENT_LENGTH * i),
            'endTime': event['startTime'] \
                + (RECORDING_SEGMENT_LENGTH * i) + RECORDING_SEGMENT_LENGTH,
            'size': 499394,
            'softReferences': [event['_id']],
            'softReferenceCount': 1,
            'referenceCount': 0,
            'streamClockOffset': 0,
            'channel': 0,
            'streamId': stream_id,
            'ts': False,
            'score': 0,
            'fileRecordingPath': recordings_path['path'],
            'cameraUuid': camera['uuid'],

        }

        yield segment


def ensure_recordings_path(db, path):
    existing_path = db.recordingPath.find_one()
    if existing_path:
        return existing_path
    db.recordingPath.insert_one({'path': path})
    return db.recordingPath.find_one()


def ensure_fake_camera(db):
    existing_camera = db.camera.find_one()
    if existing_camera:
        return existing_camera
    dirname = os.path.dirname(os.path.realpath(__file__))
    camera_json_fname = '.'.join(
        os.path.basename(__file__).split('.')[:-1]) + '_camera.json'
    with open(os.path.join(dirname, camera_json_fname), 'r') as f:
        inserted_id = db.camera.insert_one(bson.json_util.loads(f.read()))\
            .inserted_id
        return db.camera.find_one({'_id': inserted_id})

 
if __name__ == '__main__':

    import argparse

    argparser = argparse.ArgumentParser(
        description='Utility to populate fresh UniFi Video '
                    'install with dummy recordings')
    argparser.add_argument('-c',
        help='number of recordings to create', action='store',
        type=int, default=10, metavar='COUNT')
    argparser.add_argument('-k',
        help='SSH priv key path', action='store',
        default=os.path.join(os.path.expanduser('~'), '.ssh', 'id_rsa'))
    argparser.add_argument('-a',
        help='SSH host', action='store')
    argparser.add_argument('-p',
        help='SSH port', action='store', default='22')
    argparser.add_argument('-u',
        help='SSH user', action='store', default='root')
    argparser.add_argument('--ufv-path',
        help='UniFi Video data root', action='store',
        default='/usr/lib/unifi-video/data')
    argparser.add_argument('--ufv-recordings-path',
        help='UniFi Video recordings path', action='store',
        default='/usr/lib/unifi-video/data')
    argparser.add_argument('--ufv-system-user',
        help='User the UniFi Video process is running under', action='store',
        default='unfi-video')
    argparser.add_argument('mdb_uri',
        help='MongoDB URI', metavar='MONGODB_URI', action='store')

    args = argparser.parse_args()

    mongodb_host = re.match(
        r'mongodb:\/\/(?:.+?:.+?@)?(?P<host>[0-9a-z_\-.]+)(?::\/)?.*$',
        args.mdb_uri,
        re.I)
    if not mongodb_host:
        exit_with_error(
            'Invalid MongoDB URI. See '
            'https://docs.mongodb.com/manual/reference/connection-string/',
            1)

    # Use whatever host the MongoDB connection string defines when
    # no explicit SSH host is defined
    if not args.a:
        args.a = mongodb_host.group('host')

    try:
        mdb_client = pymongo.MongoClient(args.mdb_uri)
        mdb_client.admin.command('ismaster')
        av_db = mdb_client.av
    except pymongo.errors.ConnectionFailure as e:
        exit_with_error(str(e))
    
    cmd_runner = ssh_runner(args.a, args.p, args.u, args.k)

    # Test SSH binary and connection
    try:
        if 'openssh' not in subprocess.check_output(
                ['ssh', '-V'],
                stderr=subprocess.STDOUT).decode('utf8').lower():
            exit_with_error('The "ssh" command has to point to OpenSSH')
        cmd_runner(['id'])
    except subprocess.CalledProcessError:
        exit_with_error('The "ssh" command has to point to OpenSSH')

    # Create dummy files and entries in the 'av.camera', 'av.event',
    # and 'av.videoSegment' collections
    recordings_path = ensure_recordings_path(av_db, args.ufv_recordings_path)
    camera = ensure_fake_camera(av_db)
    for event in fake_events(args.c, camera, recordings_path):
        av_db.event.insert_one(event)
        print('event', str(event['_id']))
        for segment in fake_video_segments(
                event, camera, recordings_path):
            av_db.videoSegment.insert_one(segment)
            print('  segment', str(segment['_id']))
            create_fake_video_segment_file(
                cmd_runner, segment['startTime'], segment['endTime'],
                segment['streamId'], segment['streamClockOffset'],
                segment['size'], args.ufv_path, args.ufv_system_user,
                camera['uuid'])
