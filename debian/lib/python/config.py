from debian_linux.config import ConfigParser, SchemaItemList

class Config(dict):
    config_name = "defines"

    class FilepathItemList(SchemaItemList):
        def __init__(self):
            """Firmware file paths are listed in multi-line 'files' entries
            within the 'defines' file for each firmware package.

            The SchemaItemList parser that is a superclass of this one
            considers any whitespace[1] as a separator between items, but
            that prevents encoding of filepaths that contain spaces - and
            some device drivers do attempt to load firmware filenames that
            contain spaces (see #1029843 for some examples).

            This class exists to accommodate filepaths that contain spaces,
            by breaking only on whitespace that is *not* preceded by a
            backslash character.

            [1] - https://sources.debian.org/src/linux/6.5.8-1/debian/lib/python/debian_linux/config.py/#L33
            """
            # break on a single space _not_ preceded by a backslash
            # (negative lookbehind)
            super().__init__(type=r"(?<!\\) ")

        def __call__(self, i):
            """Remove escaping backslashes from the config filenames"""
            escaped_filepaths = super().__call__(i)
            filepaths = [
                escaped_filepath.replace("\\ ", " ")
                for escaped_filepath in escaped_filepaths
            ]
            assert all(filepath.strip() == filepath for filepath in filepaths)
            return filepaths

    top_schemas = {
        'base': {
            'packages': SchemaItemList(),
        },
    }

    package_schemas = {
        'base': {
            'files': FilepathItemList(),
            'support': SchemaItemList(),
            'ignore-files': SchemaItemList(),
        }
    }

    def __init__(self):
        self._read_base()

    def _read_base(self):
        config = ConfigParser(self.top_schemas)
        config.read("debian/config/%s" % self.config_name)

        packages = config['base',]['packages']

        for section in iter(config):
            real = (section[-1],) + section[:-1]
            self[real] = config[section]

        for package in packages:
            self._read_package(package)

    def _read_package(self, package):
        config = ConfigParser(self.package_schemas)
        config.read("debian/config/%s/%s" % (package, self.config_name))

        for section in iter(config):
            if len(section) > 1:
                real = (section[-1], package, '_'.join(section[:-1]))
            else:
                real = (section[-1], package)
            s = self.get(real, {})
            s.update(config[section])
            self[real] = s
