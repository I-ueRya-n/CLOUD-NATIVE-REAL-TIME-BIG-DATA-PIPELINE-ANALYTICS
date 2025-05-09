#!/bin/sh
<<<<<<< HEAD


mkdir -p ${DEPLOY_PKG}


pip install --upgrade -r ${SRC_PKG}/requirements.txt -t /tmp/dep


cp -r /tmp/dep/* ${DEPLOY_PKG}/
cp ${SRC_PKG}/*.py ${DEPLOY_PKG}/
=======
set -e

pip3 install -r ${SRC_PKG}/requirements.txt -t ${SRC_PKG}
cp -r ${SRC_PKG}/* ${DEPLOY_PKG}/
>>>>>>> 7aaad7a (Save local changes before rebase)
