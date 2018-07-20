"""
# Construct an index text file specifying the projects with the path.
"""
import sys

from ...routes import library as libroutes
from ...system import process
from ...system import files
from .. import library

def main(inv:process.Invocation) -> process.Exit:
	path, *factors = inv.args
	path = files.Path.from_path(path)

	for leading in factors:
		ls = libroutes.Segment.from_sequence(leading.split('.'))
		for fpath, fc in library.tree(path, ls):
			info = library.information(fc)
			pathstr = '.'.join(fpath.absolute)
			sys.stdout.write("%s %s\n" %(pathstr, info.identifier))

	return inv.exit(0)

if __name__ == '__main__':
	raise process.control(main, process.Invocation.system())
