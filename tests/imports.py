import unittest

class ImportTests(unittest.TestCase):

    def test_imports(self):

        import unifi_video.api
        import unifi_video.camera
        import unifi_video.collections
        import unifi_video.recording
        import unifi_video.single
        import unifi_video.utils

if __name__ == '__main__':
    import sys
    from os.path import abspath, dirname
    sys.path.append(abspath(dirname(__file__) + '/..'))
    unittest.main()
