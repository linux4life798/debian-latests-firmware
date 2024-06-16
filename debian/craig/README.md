I ran the

```bash
sudo apt install linux-support-6.8.11
. debian/craig/source-me.bash

./debian/bin/release-update . 20240610
# On main
git checkout -B master

# Same as "uscan --download-version 20240610"
uscan --download-version $(head -n1 debian/changelog | sed 's/.*\([[:digit:]]\{8\}\).*/\1/')
#
# Newest version of firmware-nonfree on remote site is 20240610, specified download version is 20240610
# Cloning into bare repository '../firmware-nonfree-temporary.3769.git'...
# remote: Enumerating objects: 3325, done.
# remote: Counting objects: 100% (3325/3325), done.
# remote: Compressing objects: 100% (2484/2484), done.
# remote: Total 3325 (delta 1120), reused 2496 (delta 742), pack-reused 0
# Receiving objects: 100% (3325/3325), 449.16 MiB | 34.27 MiB/s, done.
# Resolving deltas: 100% (1120/1120), done.
#
# gpgv: Signature made Mon Jun 10 14:23:05 2024 UTC
# gpgv:                using RSA key 4CDE8575E547BF835FE15807A31B6BD72486CFD6
# gpgv: Good signature from "Josh Boyer <jwboyer@fedoraproject.org>"
# gpgv:                 aka "Josh Boyer <jboyer@redhat.com>"
# gpgv:                 aka "Josh Boyer <jwboyer@gmail.com>"
# gpgv:                 aka "Josh Boyer <jwboyer@redhat.com>"
# Successfully repacked ../firmware-nonfree-20240610.tar.xz as ../firmware-nonfree_20240610.orig.tar.xz, deleting 255 files from it.

debian/rules orig
# mkdir -p ../orig
# tar -C ../orig -xaf ../firmware-nonfree_20240610.orig.tar.xz
# rsync --delete --exclude /debian --exclude /.git --link-dest=../orig/firmware-nonfree-20240610/ -a ../orig/firmware-nonfree-20240610/ .
# QUILT_PATCHES='/home/craig/linux-firmware/debian/patches' QUILT_PC=.pc quilt push --quiltrc - -a -q --fuzz=0
# Applying patch gitignore.patch
# 1 out of 1 hunk FAILED
# Patch gitignore.patch does not apply (enforce with -f)
# make: *** [debian/rules:69: orig] Error 1

sudo apt install rdfind python3-dacite
debian/rules debian/control
# ...
# ln: failed to create symbolic link 'debian/build/install/INT8866RCA2.bin': File exists
# debian/bin/gencontrol.py /usr/src/linux-support-6.8.11
# Traceback (most recent call last):
#   File "/home/craig/linux-firmware/debian/bin/gencontrol.py", line 341, in <module>
#     GenControl()()
#   File "/home/craig/linux-firmware/debian/bin/gencontrol.py", line 94, in __call__
#     self.do_main(packages, makefile)
#   File "/home/craig/linux-firmware/debian/bin/gencontrol.py", line 128, in do_main
#     self.do_package(packages, makefile, package, vars.copy(), makeflags.copy())
#   File "/home/craig/linux-firmware/debian/bin/gencontrol.py", line 228, in do_package
#     f, f_real, version = files_real[f]
#                          ~~~~~~~~~~^^^
# KeyError: 'cirrus/cs35l41-dsp1-spk-cali-103c896e-l0.bin'
# make[1]: *** [debian/rules:53: debian/control-real] Error 1
# make[1]: Leaving directory '/home/craig/linux-firmware'
# make: *** [debian/rules:43: debian/control] Error 2


gbp buildpackage
```
