"""
# Project protocols.
"""
import typing
import collections
import itertools

from .. import routes
from ..system import files

from . import types
from . import struct

# Directory Structure of Integrals
default_image_segment = [['system', 'architecture'], ['intention']]

# Segments noting the position of significant files in a polynomial project.
ProjectSignal = routes.Segment.from_sequence(['project.txt'])
SourceSignal = routes.Segment.from_sequence(['src'])
FactorDefinitionSignal = routes.Segment.from_sequence(['factor.txt'])

def load_project_information(file:routes.Selector):
	info = struct.parse(file.get_text_content())[1] #* ! CONTEXT: qualification required.

	return types.Information(
		info['identifier'],
		info['name'],
		info.get('icon', {}),
		info['abstract'],
		info['authority'],
		info['contact'],
	)

def factor_images(project:routes.Selector, factor:routes.Segment, directory='__f-int__'):
	"""
	# Retrieve the set of images produced by the &factor contained by &project.
	# A segment path is used to identify the factor in order to emphasize that
	# a direct file path should not be used.
	"""
	path = project//factor
	return (path * directory).delimit()

def compose_image_path(groups, default, variants:typing.Mapping, name, suffix):
	"""
	# Create a variant path (list of strings) according to the given &groups and &variants.
	"""
	segments = []

	for g in groups[:-1]:
		fields = ([(variants.get(x) or default) for x in g])
		segment = '-'.join(fields)
		segments.append(segment)

	# Final identifier.
	fields = [name]
	fields.extend((variants.get(x) or default) for x in groups[-1])
	if suffix:
		fields.append(suffix)
	segments.append('.'.join(fields))

	return segments

def parse_image_descriptor_1(string:str) -> typing.Iterator[typing.Sequence[str]]:
	"""
	# Given the data from a (system/filename)`fields.txt` file located inside
	# a factor image set directory, return an iterator producing sequences that
	# detail the groupings used to designate the location of a variant.

	# Normally unused as the default groupings are encouraged.

	# [ Parameters ]
	# /string/
		# The text format is newline separated records consisting of whitespace separated fields.
		# Each line containing fields designates a directory level that will contain
		# the variants expressed on subsequent lines. The final record designating the
		# variants used to specify the image file, often this should be "name".

		# No escaping mechanism is provided as the fields are required to be identifiers.
	"""

	for line in map(str.strip, string.split('\n')):
		if line[:1] in ('#', ''):
			# Ignore comments and empty lines.
			continue

		# Strip the fields in each group ignoring empty fields.
		yield [x for x in map(str.strip, line.split()) if x]

class V1(types.Protocol):
	"""
	# polynomial-1 protocol implementation.
	"""

	identifier = 'polynomial-1'
	implicit_types = {
		'exe': 'executable',
		'ext': 'extension',
		'lib': 'library',
		'arch': 'archive',
		'part': 'partial',
	}

	def information(self, project:routes.Selector, filename="project.txt") -> types.Information:
		"""
		# Retrieve the information record of the project.
		"""
		return load_project_information(project / filename)

	def infrastructure(self, absolute, route, filename="infrastructure.txt") -> types.ISymbols:
		"""
		# Extract and interpret infrastructure symbols used to expresss abstract requirements.
		"""
		ifp = (route/filename)

		if ifp.fs_type() == 'data':
			return {
				k: [
					tuple(t[1].split('#', 1))
					if (t[0].split("/", 3)[:2]) == ['reference', 'hyperlink']
					else tuple(map(str, absolute(t[1])))
					for t in v
				]
				for k, v in struct.parse(ifp.get_text_content())[1].items()
				if not isinstance(v, struct.Paragraph)
			}
		else:
			return {}

	def image(self,
			route:types.ProjectDirectory,
			variants,
			fp:types.FactorPath,
			default='void',
			groups=default_image_segment,
			suffix='i'
		) -> routes.Selector:
		"""
		# Retrieve the location of the factor's image for the given variants.
		"""
		idir = factor_images(route, fp)
		seg = compose_image_path(groups, default, variants, fp.identifier, suffix)
		return (idir + seg)
	integral = image

	def isource(self, route:files.Path):
		"""
		# Determine if the route is a possible source file for a factor.
		"""
		has_delimiter = ('.' in route.identifier)

		if has_delimiter:
			if route.identifier.startswith('.'):
				# File with leading `.`
				return False
		else:
			# file has no extension to identify its project local type.
			if route.fs_type() == 'data':
				return False

		return True

	def factor_structs(self, paths:typing.Iterable[files.Path], _nomap={}):
		"""
		# Given an iterable of paths identifying whole factors, resolve their
		# domain and type using the (id)`source-extension-map` parameter and
		# the file's dot-extension.
		"""
		extmap = self.parameters.get('source-extension-map', _nomap)

		for p in paths:
			name, suffix = p.identifier.rsplit('.')
			ftype, symbols = extmap.get(suffix, ('unknown', set()))
			yield (name, ftype), (symbols, [p])

	def collect_sources(self, route:files.Path):
		"""
		# Collect source files for a composite.
		"""
		return (
			y for y in
			itertools.chain.from_iterable(
				x[1] for x in route.delimit().fs_index('data')
				if not x[0].identifier.startswith('.')
			)
			if not y.identifier.startswith('.')
		)

	def iterfactors(self, route:files.Path, ignore=types.ignored) -> typing.Iterable[types.FactorType]:
		"""
		# Query the &route for factors.
		"""

		name = route.identifier
		path = ()
		cur = collections.deque([(route, path)])

		while cur:
			r, path = cur.popleft()
			segment = types.FactorPath.from_sequence(path)

			assert r.identifier not in ignore # cache or integration directory

			srcdir = r//SourceSignal
			spec = r//FactorDefinitionSignal

			if srcdir.fs_type() == 'directory' and spec.fs_type() == 'data':
				# Explicit composite.
				spec_ctx, data = struct.parse(spec.get_text_content())

				sources = self.collect_sources(srcdir)
				cpath = types.FactorPath.from_sequence(path)

				yield (cpath, data['type']), (data.get('symbols', set()), sources)

				dirs = ()
				files = r.fs_iterfiles('data')
			else:
				dirs, files = r.fs_list('data')

			for (name, ftype), fstruct in self.factor_structs([x for x in files if self.isource(x)]):
				yield ((segment/name), ftype), fstruct

			for x in dirs:
				if x.identifier in ignore:
					continue

				if '.' not in x.identifier:
					cur.append((x, path + (x.identifier,)))
				else:
					# Implicit composite: .exe, .lib, .ext
					factor_id, factor_type = x.identifier.rsplit('.', 1)
					itype = self.implicit_types.get(factor_type)

					if itype:
						cpath = types.FactorPath.from_sequence(path+(factor_id,))
						sources = self.collect_sources(x)
						yield (cpath, itype), (set(), sources)
					else:
						# No a recognized implicit type.
						pass
			del dirs, files

if __name__ == '__main__':
	import sys
	proto = V1({})
	for x in sys.argv[1:]:
		path = files.Path.fs_select(x)
		info = load_project_information(path/'project.txt')

		with (path/'.protocol').fs_open('tw') as f:
			pdata = '%s %s\n' %(info.identifier, 'factors/polynomial-1')
			f.write(pdata)
