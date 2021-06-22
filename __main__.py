#!/usr/bin/env python3

import collections
import hashlib
import pathlib
import random
import subprocess
import sys
import zipfile

import click
import flask

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".JPG", ".png", ".gif"}

def _hash(data):
    H = hashlib.md5()
    H.update(bytes(data, "utf-8"))
    return H.hexdigest()

def _get_mimetype(image):
    out = subprocess.run([
        "file", "--mime-type", "--brief", "-"],
        input=image, capture_output=True)
    return out.stdout.decode().strip()

class Galleries:
    "represents a collection of galleries"

    def __init__(self):
        # image_id -> Union[RegularImage, ArchivedImage]
        self.images = dict()
        # gallery_id -> List[Union[RegularImage, ArchivedImage]]
        self.image_galleries = collections.defaultdict(list)
        # gallery_id -> gallery_name
        self.gallery_names = dict()
        # gallery_id -> pathlib.Path
        self.gallery_locations = dict()

    def insert_image(self, image):
        "add a new image to the collection"
        self.images[image.image_id] = image
        self.image_galleries[image.gallery_id] += [image]

        self.gallery_names[image.gallery_id] = image.gallery_name
        self.gallery_locations[image.gallery_id] = image.gallery_location

    def get_image(self, image_id) -> bytes:
        "get the contents of an image file"
        return self.images[image_id].get()

    def get_gallery_names(self):
        "get a sorted list of (gallery_id, gallery_name) pairs"
        return sorted(self.gallery_names.items(), key=lambda x: x[1])

    def get_gallery_name(self, gallery_id):
        "get the name of an individual gallery"
        return self.gallery_names[gallery_id]

    def random_images(self, gallery_id, k=3):
        "get some random images from a gallery"
        return random.choices(self.image_galleries[gallery_id], k=k)

class Image:
    pass

class RegularImage(Image):
    "represents an image stored as a regular file"
    def __init__(self, file: pathlib.Path):
        self.file = file
        self.gallery = file.parent

    def get(self) -> bytes:
        return self.file.open("rb").read()

    @property
    def gallery_id(self):
        return _hash(str(self.gallery))

    @property
    def gallery_name(self):
        return str(self.gallery)

    @property
    def gallery_location(self):
        return self.gallery

    @property
    def image_id(self):
        return _hash(str(self.file))

    @property
    def image_name(self):
        return self.file.name

class ArchivedImage(Image):
    "represents an image stored inside an archive"
    def __init__(self, archive: pathlib.Path, gallery: pathlib.Path, file: str):
        self.archive = archive
        self.gallery = gallery
        self.file = file

    def get(self) -> bytes:
        with zipfile.ZipFile(self.archive) as z:
            return z.open(str(self.gallery/self.file)).read()

    @property
    def gallery_id(self):
        return _hash(str(self.archive/self.gallery))

    @property
    def gallery_name(self):
        return str(self.archive) + " → " + str(self.gallery)

    @property
    def gallery_location(self):
        return self.archive

    @property
    def image_id(self):
        return _hash(str(self.gallery/self.file))

    @property
    def image_name(self):
        return self.file

def get_files(root: pathlib.Path, accelerate: bool):
    "recursively yield an iterable of Image objects that are under `root`"
    if root.name.startswith("._"):
        return
    if root.is_file():
        # if root is an image, yield a RegularImage object
        if root.suffix in _IMAGE_EXTENSIONS:
            yield RegularImage(root)
        # if root is an archive, yield the images it contains
        elif (accelerate and root.suffix == ".zip") or \
            (not accelerate and zipfile.is_zipfile(root)):
            with zipfile.ZipFile(root) as z:
                for afile in z.infolist():
                    file = pathlib.Path(afile.filename)
                    if file.suffix in _IMAGE_EXTENSIONS:
                        yield ArchivedImage(root, file.parent, file.name)
    # if root is a directory, call get_files on its children
    if root.is_dir():
        for child in root.iterdir():
            yield from get_files(child, accelerate)

def make_app(roots, galleries):
    script_location = pathlib.Path(sys.argv[0])
    template_folder = script_location.parent/"templates"
    app = flask.Flask("gallery preview", template_folder=template_folder)

    @app.route("/")
    def index():
        data = {
                "name": ", ".join(map(str, roots)),
                "galleries": galleries
                }
        return flask.render_template("index.html", **data)

    @app.route("/<image_id>/<image_name>")
    def image(image_id, image_name):
        image = galleries.get_image(image_id)

        mimetype = _get_mimetype(image)
        return flask.Response(image, mimetype=mimetype)

    @app.route("/gallery/<gallery_id>")
    def gallery(gallery_id):
        data = {
                "root": galleries.get_gallery_name(gallery_id),
                "images": galleries.image_galleries[gallery_id]
                }
        return flask.render_template("gallery.html", **data)

    @app.route("/reveal/<gallery_id>", methods=["POST"])
    def reveal(gallery_id):
        subprocess.run(["open", "-R", str(galleries.gallery_locations[gallery_id])])
        return flask.make_response({}, 200)

    return app

@click.command()
@click.argument("roots", nargs=-1, type=click.Path(exists=True), required=True)
@click.option("--port", "-p", default=5000, show_default=True)
@click.option("--host", "-h", default="127.0.0.1", show_default=True)
@click.option("--check-archives", "-c", is_flag=True, help="Instead of using a file's extension to determine if it's an archive, use Python's zipfile.is_zipfile instead.")
def cli(roots, port, host, check_archives):
    accelerate = not check_archive

    galleries = Galleries()

    roots = map(pathlib.Path, roots)
    roots = tuple(roots)
    for root in roots:
        for image in get_files(root, accelerate):
            galleries.insert_image(image)

    app = make_app(roots, galleries)
    app.run(threaded=True, host=host, port=port)

if __name__ == "__main__":
    cli()
