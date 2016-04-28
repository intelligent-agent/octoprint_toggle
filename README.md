OctoPrint Plugin for Toggle
=========================

Toggle is a user interface for Redeem.

This plugin allows restart and configuration of Toggle from OctoPrint.

How to make debian package: 
python setup.py sdist
cd dist
py2dsc-deb -m "Your name <you@yourdomain.com>" OctoPrint-Toggle-0.4.tar.gz

Note: 
Build fails, update /usr/lib/python2.7/dist-packages/octoprint_setuptools/__init__.py
with all={}
