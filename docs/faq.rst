.. _faq:

Frequently asked questions
==========================

How do I use it with an untested version of UniFi Video?
--------------------------------------------------------

Use the keyword argument ``check_ufv_version`` when creating an API instance:

.. code-block:: python

   from unifi_video import UnifiVideoAPI
   uva = UnifiVideoAPI(api_key='xxxxxx', addr='10.3.2.1', check_ufv_version=False)

How to skip cert verification?
------------------------------

Use the keyword argument ``verify_cert`` when creating an API instance:

.. code-block:: python

   from unifi_video import UnifiVideoAPI
   uva = UnifiVideoAPI(api_key='xxxxxx', addr='10.3.2.1', verify_cert=False)

How do I use an open file descriptor, or another file-like object to save a snapshot with?
------------------------------------------------------------------------------------------
The `filename` param of :func:`~unifi_video.camera.UnifiVideoCamera.snapshot` can be set to
``True`` to force the method to return the raw response body. You can then do with it as you
please.

.. code-block:: python

   from unifi_video import UnifiVideoAPI

   uva = UnifiVideoAPI(api_key='xxxxxx', addr='10.3.2.1')
   camera = uva.get_camera('Garage')

   some_file_like_object.write(camera.snapshot(filename=True))

This goes for all the download methods:

- :func:`unifi_video.camera.UnifiVideoCamera.snapshot`
- :func:`unifi_video.camera.UnifiVideoCamera.recording_between`
- :func:`unifi_video.recording.UnifiVideoRecording.snapshot`
- :func:`unifi_video.recording.UnifiVideoRecording.download`

What is the difference between the three camera collections?
------------------------------------------------------------
A :class:`UnifiVideoAPI` object has three camera collections:

.. code-block:: python

   from unifi_video import UnifiVideoAPI

   uva = UnifiVideoAPI(api_key='xxxxxx', addr='10.3.2.1')

   for camera in uva.cameras:
     print(camera)

   for camera in uva.active_cameras:
     print(camera)

   for camera in uva.managed_cameras:
     print(camera)

:attr:`UnifiVideoAPI.cameras`
+++++++++++++++++++++++++++++
Contains every camera the associated UniFi Video server is aware of. These
could be anything from an unmanaged camera on the network to an old long ago
removed camera that still has a lingering database entry.

:attr:`UnifiVideoAPI.managed_cameras`
+++++++++++++++++++++++++++++++++++++
Only contains cameras that are managed by the UniFi Video server. Note that
this does not exclude cameras that are offline.

:attr:`UnifiVideoAPI.active_cameras`
++++++++++++++++++++++++++++++++++++
Cameras that are both managed by the UniFi Video server and currently online.

unifi-video-api, unifi-video, unifi_video: which is it?
-------------------------------------------------------
`unifi-video-api` is the name of the `Github repository <https://github.com/yuppity/unifi-video-api>`_,
`unifi_video` is the name of the `python package <https://github.com/yuppity/unifi-video-api/tree/master/unifi_video>`_,
and `unifi-video` is the name of the `PyPI package <https://pypi.org/project/unifi-video/>`_ that contains the `unifi_video`
python package.
