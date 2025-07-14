#!/bin/bash
# Create a tag/release description message.
#
# Usage:
# ./release-message.sh <upstream_tag> <changelog_range_refspec>
#
# Example:
# ./release-message.sh 20250708 20250627-1..20250708

main() {
	local upstream_tag="$1"
	local changelog_range_refspec="$2"

	echo "Pure linux-firmware version ${upstream_tag} for Debian"
	echo

	echo "Changelog:"
	echo
	git log --pretty=format:"%h%d %s [%an]" "${changelog_range_refspec}" | cat
	echo
}

main "$@"
