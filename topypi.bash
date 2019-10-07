#!/usr/bin/env bash

PKG_NAME="$(sed -n 's/.*pypi_package_name *= *["'"'"']\(.*\)["'"'"'].*/\1/p' setup.py)"
DIST_DIR=_dist_"${PKG_NAME}"

clean() {
  rm -rfv "${DIST_DIR}"
  rm -rfv "${PKG_NAME}"*.egg-info
}

build_dist() {
  python3 setup.py sdist --dist-dir "${DIST_DIR}"
}

upload() {
  if [ ! -z $1 ]; then
    python3 -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*.tar.gz
  else 
    python3 -m twine upload dist/*.tar.gz
  fi
}

case $1 in

  test)
    clean && build_dist && upload totest
    clean
    ;;

  build)
    clean && build_dist
    ;;

  *)
    clean && build_dist && upload
    clean

esac
