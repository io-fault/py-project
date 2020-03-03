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
		info['controller'],
		info['contact'],
	)

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

	def information(self, fc:types.FactorContextPaths, filename="project.txt") -> types.Information:
		"""
		# Retrieve the information record of the project.
		"""
		return load_project_information(fc.project / filename)

	from . import library as _legacy

	def infrastructure(self, fc:types.FactorContextPaths, filename="infrastructure.txt") -> types.ISymbols:
		"""
		# Extract and interpret infrastructure symbols used to expresss abstract requirements.
		"""
		infra = {}
		i_sources = [
			(x/'context'/filename)
			for x in (fc.root >> fc.context)
			if x is not None
		]

		i_sources.append(fc.project/filename)

		for x in i_sources:
			if x.exists():
				ctx, content = struct.parse(x.get_text_content())
				infra.update(content)

		uinfra = {
			k: v.__class__([
				t[1]
				if (t[0].split("/", 3)[:2]) == ['reference', 'hyperlink']
				else self._legacy.universal(fc, fc.factor(), t[1])
				for t in v
			])
			for k, v in infra.items()
			if not isinstance(v, struct.Paragraph)
		}

		return uinfra

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

	def factor_structs(self, paths:typing.Iterable[files.Path]):
		"""
		# Given an iterable of paths identifying whole factors, resolve their
		# domain and type using the (id)`source-extension-map` parameter and
		# the file's dot-extension.
		"""
		extmap = self.parameters.get('source-extension-map')

		for p in paths:
			name, suffix = p.identifier.rsplit('.')
			fdomain, ftype, symbols = extmap.get(suffix, ('data', 'library', set()))
			yield (name, (fdomain, ftype, symbols, [p]))

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

				yield (cpath, (data['domain'], data['type'], data.get('symbols', set()), sources))

				dirs = ()
				files = r.fs_iterfiles('data')
			else:
				dirs, files = r.fs_list('data')

			for name, fstruct in self.factor_structs([x for x in files if self.isource(x)]):
				yield (segment/name), fstruct

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
						yield (cpath, ('system', itype, set(), sources))
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
