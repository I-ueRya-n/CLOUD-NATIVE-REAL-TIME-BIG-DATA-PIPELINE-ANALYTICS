#!/bin/sh


mkdir -p ${DEPLOY_PKG}


pip install --upgrade -r ${SRC_PKG}/requirements.txt -t /tmp/dep


cp -r /tmp/dep/* ${DEPLOY_PKG}/
cp ${SRC_PKG}/*.py ${DEPLOY_PKG}/
