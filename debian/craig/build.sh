#!/bin/bash
# Craig Hesling <craig@hesling.com>

main() {
    export PYTHONPATH=/usr/share/linux-support-6.7.12/lib/python

    echo "Starting build process..."

    # Install necessary packages
    echo "Installing necessary packages..."
    sudo apt-get update
    sudo eatmydata apt-get install --no-install-recommends -y make dpkg-dev debhelper devscripts git python3 python3-dacite python3-jinja2 quilt rsync

    # Parse changelog version information
    local version=$(dpkg-parsechangelog -SVersion)
    local upstream_version=$(echo "${version}" | sed 's/-[^-]*$//')

    echo "Generating orig tarball..."
    origtargz -dt
    echo "Orig tarball generated successfully."

    echo "Running debian/rules orig..."
    debian/rules orig
    echo "debian/rules orig completed successfully."

    # Fudge source version and suite
    echo "Adjusting version in changelog..."
    sed -i -e '1 s/) [^;]*/+salsaci) UNRELEASED/' debian/changelog
    version+="+salsaci"

    # Run gencontrol.py
    echo "Generating control files..."
    local log="$(mktemp)"
    # This is designed to fail.
    debian/rules debian/control-real |& tee "${log}"
    if [[ ${PIPESTATUS[0]} -ne 2 ]]; then
        echo "Error: Control files generation failed."
        exit 1
    fi
    if ! grep -q 'been generated SUCCESSFULLY' "${log}"; then
        echo "Error: Control files not generated successfully."
        exit 1
    fi

    # Build the package
    echo "Building the package..."
    # dpkg-buildpackage arguments:
    # -uc: Do not sign the .changes file
    # -us: Do not sign the source package
    # -S: Create a source package only (no binary packages)
    # -sa: Include original source (forces inclusion of the original source)
    # -d: Do not check build dependencies and conflicts
    dpkg-buildpackage -uc -us -S -sa -d

    # Move artifacts to a specific directory
    WORKING_DIR="./artifacts"
    mkdir -p ${WORKING_DIR}
    cp ../firmware-nonfree_${upstream_version}.orig.tar.xz ${WORKING_DIR}
    mv ../firmware-nonfree_${version}.dsc ../firmware-nonfree_${version}.debian.tar.xz ../firmware-nonfree_${version}_source.buildinfo ../firmware-nonfree_${version}_source.changes ${WORKING_DIR}

    # Skip the source to build process. Just build the binary package.
    dpkg-buildpackage -uc -us -b

    echo "Build process completed successfully."
}


main "$@"
