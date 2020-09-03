# CHANGELOG

## 0.1.7 (2020-04-14)

### Added
* Included *UVC G4 Bulle*t and *UVC G4 Pro* in the list of supported camera
  models

### Changed
* Expanded the supported versions range to include the latest UniFi Video,
  [v3.10.11][ufv31011].

## 0.1.6 (2020-01-19)

### Fixed
* Guard against `get()` on potential NoneType (occurred while instantiating
  `UnifiVideoCamera` against unmanaged camera)

## 0.1.5 (2019-12-08)

### Fixed
* Bug in camera model check

## 0.1.4 (2019-10-20)

### Added
* `UnifiVideoCamera.get_recording_settings()` (#8)

### Changed
* Renamed underscored names `_version` and `_name` in `UnifiVideoAPI` to
  signal it is OK to rely on them in application code (#9)

## 0.1.3 (2019-10-16)

### Added
* Expanded supported versions range to cover UniFi Video versions
  3.10.7 - 3.10.10

## 0.1.2 (2019-10-14)

### Added
* Documentation
* `UnifiVideoCamera.snapshot()`: `width` keyword arg

### Changed
* `method` keyword argument in `UnifiVideoAPI.post()` renamed to `_method`

[ufv31011]: https://community.ui.com/releases/UniFi-Video-3-10-11/e4b60ac8-5c9a-4763-9b59-e97d848d4c86
