"""
# Extensible project protocol for filesystem directories.
"""
import typing
import collections
import itertools

from ..context.types import Cell
from ..route.types import Segment, Selector
from ..system import files

from . import types
from . import struct

# Directory Structure of Integrals
default_image_segment = [['system', 'architecture'], ['intention']]

# Segments noting the position of significant files in a polynomial project.
ProjectSignal = Segment.from_sequence(['project.txt'])
SourceSignal = Segment.from_sequence(['src'])
FactorDefinitionSignal = Segment.from_sequence(['factor.txt'])

def load_project_information(file:Selector):
	info = struct.parse(file.get_text_content())[1] #* ! CONTEXT: qualification required.

	return types.Information(
		info['identifier'],
		info['name'],
		info.get('icon', {}),
		info['abstract'],
		info['authority'],
		info['contact'],
	)

def factor_images(project:Selector, factor:Segment, directory='__f-int__'):
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

	def information(self, project:Selector, filename="project.txt") -> types.Information:
		"""
		# Retrieve the information record of the project.
		"""
		return load_project_information(project / filename)

	def infrastructure(self, absolute, route,
			filename="infrastructure.txt",
			Reference=types.Reference,
		) -> types.ISymbols:
		"""
		# Extract and interpret infrastructure symbols used to expresss abstract requirements.
		"""
		ifp = (route/filename)
		sym = {}

		if ifp.fs_type() != 'data':
			return sym

		for k, refs in struct.parse(ifp.get_text_content())[1].items():
			if isinstance(refs, struct.Paragraph):
				# Symbol documentation.
				continue

			sym[k] = list()
			for typ, method, refdata in refs:
				# Combine source with identified project and factor.
				# (method, project, factor)
				iso = None

				if typ == 'absolute':
					project, factor = refdata.rsplit('/', 1)
					if '#' in factor:
						factor, iso = factor.rsplit('#', 1)

					sym[k].append(Reference(project, types.factor@factor, method, iso))
				elif typ == 'relative':
					project, factor = absolute(refdata)
					sym[k].append(Reference(project, factor, None, None))
				else:
					raise Exception("unrecognized reference type, expecting absolute or relative")

		return sym

	def inherit(self, context, infrastructure):
		"""
		# Inherit information and configuration from a context project.
		"""

		if 'source-extension-map' not in self.parameters:
			self.parameters['source-extension-map'] = {}

		extmap = []
		try:
			extmap.extend(context.parameters['source-extension-map'].items())
		except Exception:
			# Ignore most errors here.
			# Resetting extmap for safety may be appropriate, but it is not clear.
			pass

		extmap.extend(self.parameters['source-extension-map'].items())
		self.parameters['source-extension-map'] = dict(extmap)

		extmap = self.parameters['source-extension-map']
		for k, symrefs in infrastructure:
			kstr = k.strip()
			if kstr[:2] != '*.':
				# Symbol is not a suffix pattern.
				continue

			type_reqs = set()

			for ref in symrefs:
				if ref.method != 'type':
					# Factor is not recognized as a type.
					continue

				extmap[kstr[2:]] = (ref.isolation, ref.project, ref.factor, {kstr})

	def image(self,
			route:types.Path,
			variants,
			fp:types.FactorPath,
			default='void',
			groups=default_image_segment,
			suffix='i'
		) -> Selector:
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
		default = (None, 'http://if.fault.io/factors/', 'unknown', set())
		extmap = self.parameters.get('source-extension-map', _nomap)

		for p in paths:
			name, suffix = p.identifier.rsplit('.')
			stype, pj_url, ftype, symbols = extmap.get(suffix, default)
			yield (name, ftype), (symbols, Cell(p.container.delimit()/p.identifier))

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

	def iterfactors(self, route:files.Path, rpath:types.FactorPath, ignore=types.ignored) -> typing.Iterable[types.FactorType]:
		"""
		# Query the project &route for factor compositions contained within &rpath.
		"""

		froute = route // rpath
		name = rpath.identifier
		path = ()
		cur = collections.deque([(froute, path)])

		while cur:
			r, path = cur.popleft()
			segment = types.FactorPath.from_sequence(path)

			assert r.identifier not in ignore # cache or integration directory

			srcdir = r//SourceSignal
			spec = r//FactorDefinitionSignal

			if srcdir.fs_type() == 'directory' and spec.fs_type() == 'data':
				# Explicit Typed Factor directory.
				spec_ctx, data = struct.parse(spec.get_text_content())

				sources = self.collect_sources(srcdir)
				cpath = types.FactorPath.from_sequence(path)

				yield (cpath, data['type']), (data.get('symbols', set()), sources)

				dirs = ()
				# Filter factor.txt and abstract.txt from possible factors.
				files = [x for x in r.fs_iterfiles('data') if x.identifier not in {'factor.txt', 'abstract.txt'}]
			else:
				# Not an Explicitly Typed Factor directory.
				dirs, files = r.fs_list('data')

			# Recognize Indirectly Typed Factors.
			for (name, ftype), fstruct in self.factor_structs([x for x in files if self.isource(x)]):
				yield ((segment/name), ftype), fstruct

			# Factor Index.
			for x in dirs:
				if x.identifier in ignore:
					continue

				if '.' not in x.identifier:
					cur.append((x, path + (x.identifier,)))
				else:
					pass

			del dirs, files

if __name__ == '__main__':
	import sys
	proto = V1({})
	for x in sys.argv[1:]:
		path = files.root.fs_select(x)
		info = load_project_information(path/'project.txt')

		with (path/'.protocol').fs_open('tw') as f:
			pdata = '%s %s\n' %(info.identifier, 'factors/polynomial-1')
			f.write(pdata)
