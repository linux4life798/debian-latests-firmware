from debian_linux.config import ConfigParser, SchemaItemList

class Config(dict):
    config_name = "defines"

    class FilepathItemList(SchemaItemList):
        def __init__(self):
            """Firmware filenames are listed one-per-line in each 'defines'
            file, but newlines are removed during conversion of the entries.
            That means that backslash-escaped spaces are used to identify
            spaces within filenames.  Use a pattern that splits on any spaces
            NOT preceded by a backslash.
            """
            super().__init__(type=r"(?<!\\)\s+")

        def __call__(self, i):
            """Remove escaping backslashes from the config filenames"""
            filepaths = super().__call__(i)
            return [filepath.replace("\\ ", " ") for filepath in filepaths]

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
