"""
# Project directory protocol for explicit factor specifications.

# Explicitly Typed Factors is a project factor protocol designed for projects
# that primarily consist of factors that are composed of single source files.
# Notably, languages such as Interpreted Lisps and Python are likely users of &.explicit.

# Composites are designated as directories containing a (filename)`src` directory and a
# (filename)`factor.txt` file. When present, &query will associate the tree contained in
# the source directory as the sources composing the factor whose type is designted in
# the, previously mentioned, text file. All other directories are perceived to contain
# Whole Factors whose (term)`domain` is inferred from the file's identified language.
"""
import collections

from . import core
from ..text import struct

def isource(route):
	"""
	# Determine if the route is considered to be a source file for
	# a composite factor.
	"""
	has_delimiter = ('.' in route.identifier)

	if has_delimiter:
		if route.identifier.startswith('.'):
			# File with leading `.`.
			return False
	else:
		# file has no extension to identify its project local type.
		if route.type() == 'file':
			return False

	return True

def query(route, ignore=core.ignored):
	"""
	# Query for identifying composite factors from an explicitly typed tree.
	"""

	whole = {}
	composites = {}

	name = route.identifier
	path = ()
	cur = collections.deque([(route, path)])

	while cur:
		r, path = cur.popleft()
		assert r.identifier not in ignore # cache or integration directory

		if (r/'src').exists() and (r/'factor.txt').exists():
			whole[path] = ('factor', 'directory', {}, r.files())

			src = (r/'src')
			spec = (r/'factor.txt')
			spec_ctx, data = struct.parse(spec.get_text_content())

			sources = src.tree()[1] # Only interested in regular files.
			sources = [src.__class__(src, (src>>x)[1]) for x in sources]
			composites[path] = (data['domain'], data['type'], data.get('symbols', set()), sources)
		else:
			dirs, files = r.subnodes()
			whole[path] = (
				'factor', 'directory', {},
				[x for x in files if isource(x)]
			)

			cur.extend([
				(x, path + (x.identifier,)) for x in dirs
				if x.identifier not in ignore and '.' not in x.identifier
			])

	return whole, composites
