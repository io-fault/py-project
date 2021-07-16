"""
# Extensible project protocol for filesystem directories.
"""
import typing
import collections
import itertools
import functools

from ..context.types import Cell
from ..route.types import Segment, Selector
from ..system import files

from . import types
from . import struct

# Directory Structure of Integrals
default_image_segment = [['system', 'architecture'], ['intention']]
unknown_factor_type = types.Reference(
	'http://if.fault.io/factors', types.factor@'image.unknown',
	'type', None
)
image_factor_type = types.Reference(
	'http://if.fault.io/factors', types.factor@'image.reflection',
	'type', None
)

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
	path = project // factor
	return (path * directory).delimit()

def compose_image_path(groups, default, variants, name, suffix):
	"""
	# Create a variant path (list of strings) according to the given &groups and &variants.
	"""
	segments = []

	for g in groups[:-1]:
		fields = ([(variants.get(x) or default) for x in g])
		segment = '-'.join(fields)
		segments.append(segment)

	if variants.get('form'):
		segments.append(variants.get('form'))

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
					sym[k].append(Reference.from_ri(method, refdata))
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

			# Identify the factor type with the `type` method.
			for ref in symrefs:
				if ref.method == 'type':
					# Factor is not recognized as a type.
					extmap[kstr[2:]] = (ref, {kstr})
					break
			else:
				# No 'type' requirement provided by format symbol.
				pass

	def image(self, route:types.Path, variants, fp:types.FactorPath, *,
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

	def source_format_resolution(self):
		"""
		# Construct a resolution (type) cache for the source extension map.
		"""

		try:
			mapping = self.parameters['source-extension-map']
		except KeyError:
			# No map available.
			return (lambda x: (unknown_factor_type, set()))
		else:
			return functools.lru_cache(16)(lambda x: mapping.get(x, (unknown_factor_type, set())))

	def indirect_factor_records(self, typcache, paths:typing.Iterable[files.Path],
			*, _nomap={}, _default=(unknown_factor_type, set()),
		):
		"""
		# Given an iterable of paths identifying Indirectly Typed Factors, resolve their
		# type reference, factor type, and symbols using the given &typcache.
		"""

		for p in paths:
			# Normalize path; the delimited partition may be used by callers.
			src = p.container.delimit() / p.identifier

			name, suffix = src.identifier.split('.')
			ref, symbols = typcache(suffix)
			yield (name, ref.isolate(None)), (symbols, Cell((ref, src)))

	def collect_explicit_sources(self, typcache, route:files.Path):
		"""
		# Collect source files paired with their type reference for an
		# Explicitly Typed Factor record.
		"""

		# Excluding dot-directories.
		files = (
			x[1] for x in route.delimit().fs_index('data')
			if not x[0].identifier.startswith('.')
		)

		# Excluding dot-files.
		for y in itertools.chain.from_iterable(files):
			if not y.identifier.startswith('.'):
				yield (typcache(y.extension)[0], y)

	def iterfactors(self, route:files.Path, rpath:types.FactorPath,
			*, ignore=types.ignored
		) -> typing.Iterable[types.FactorType]:
		"""
		# Query the project &route for factor specifications contained within &rpath.
		"""

		froute = route // rpath
		name = rpath.identifier
		path = ()
		cur = collections.deque([(froute, path)])
		typcache = self.source_format_resolution()

		while cur:
			r, path = cur.popleft()
			segment = types.FactorPath.from_sequence(path)

			assert r.identifier not in ignore # cache or integration directory

			srcdir = r // SourceSignal
			spec = r // FactorDefinitionSignal

			if srcdir.fs_type() == 'directory' and spec.fs_type() == 'data':
				# Explicit Typed Factor directory.
				spec_ctx, data = struct.parse(spec.get_text_content())

				sources = self.collect_explicit_sources(typcache, srcdir)
				cpath = types.FactorPath.from_sequence(path)

				typref = types.Reference.from_ri('type', data['type'])
				yield (cpath, typref), (data.get('symbols', set()), sources)

				dirs = ()
				# Filter factor.txt and abstract.txt from possible factors.
				files = [
					x for x in r.fs_iterfiles('data')
					if x.identifier not in {'factor.txt', 'abstract.txt'}
				]
			else:
				# Not an Explicitly Typed Factor directory.
				dirs, files = r.fs_list('data')

			# Recognize Indirectly Typed Factors.
			ifr = self.indirect_factor_records(typcache, [x for x in files if self.isource(x)])
			for (name, ftype), fstruct in ifr:
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
