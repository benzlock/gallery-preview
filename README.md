# gallery-preview

`gallery-preview` is a utility for viewing image galleries in your browser. It provides a script with the following usage pattern:

```
Usage: python -m  [OPTIONS] ROOTS...

Options:
  -p, --port INTEGER    [default: 5000]
  -h, --host TEXT       [default: 127.0.0.1]
  -c, --check-archives  Instead of using a file's extension to determine if
                        it's an archive, use Python's zipfile.is_zipfile
                        instead.
  --help                Show this message and exit.
```

`gallery-preview` opens a Web interface (on local port 5000 by default) that shows image files grouped by their parent directory.

`ROOTS` should be a list containing files or directories. These will be treated as follows:
 * any images in the list are added to the list of images to be previewed,
 * any directories in the list are recursively searched for images to be previewed, and
 * the contents of any zip files in the list are searched for images to be previewed.

This depends on the `file` and `open` utilities, which are definitely available in macOS; I don't know about other operating systems.
