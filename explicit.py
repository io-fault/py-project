"""
# Project Directory Protocol for explicit factor specifications.

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

from .. import routes

from . import core
from . import struct

ProjectSignal = routes.Segment.from_sequence(['project.txt'])
ContextSignal = routes.Segment.from_sequence(['context', 'project.txt'])
SourceSignal = routes.Segment.from_sequence(['src'])
FactorDefinitionSignal = routes.Segment.from_sequence(['factor.txt'])

class ProtocolViolation(Exception):
	"""
	# The route was identified as not conforming to the protocol.
	"""

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
		if route.fs_type() == 'data':
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

		srcdir = r//SourceSignal
		spec = r//FactorDefinitionSignal

		if srcdir.fs_type() == 'directory' and spec.fs_type() == 'data':
			whole[path] = ('factor', 'directory', {}, list(r.fs_iterfiles('data')))

			spec_ctx, data = struct.parse(spec.get_text_content())

			srcdir = srcdir.delimit()
			sources = srcdir.tree()[1] # Only interested in regular files.
			cpath = routes.Segment.from_sequence(path)
			composites[cpath] = (data['domain'], data['type'], data.get('symbols', set()), sources)
		else:
			dirs, files = r.fs_list()
			whole[path] = (
				'factor', 'directory', {},
				[x for x in files if isource(x)]
			)

			cur.extend([
				(x, path + (x.identifier,)) for x in dirs
				if x.identifier not in ignore and '.' not in x.identifier
			])

	return whole, composites
