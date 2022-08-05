#!/usr/bin/env python3
"""
Wiktio: simple and memory-efficient word extractor for Wiktionary

XML dump file (bz2-compressed) -> list of page titles (plaintext)
"""

# ============================================================================ #

import argparse
import re
import sys
from bz2 import BZ2File

from lxml import etree
from tqdm import tqdm

# ============================================================================ #


def fast_iter(context, func, *args, **kwargs):
	"""
	http://lxml.de/parsing.html#modifying-the-tree
	Based on Liza Daly's fast_iter
	http://www.ibm.com/developerworks/xml/library/x-hiperfparse/
	See also http://effbot.org/zone/element-iterparse.htm
	https://stackoverflow.com/questions/12160418/why-is-lxml-etree-iterparse-eating-up-all-my-memory
	"""
	for event, elem in tqdm(context,
	                        unit='elem',
	                        desc='XML tree elements parsed'):
		func(elem, *args, **kwargs)
		# It's safe to call clear() here because no descendants will be accessed
		elem.clear()
		# Also eliminate now-empty references from the root node to elem
		for ancestor in elem.xpath('ancestor-or-self::*'):
			while ancestor.getprevious() is not None:
				del ancestor.getparent()[0]
	del context

# ============================================================================ #


def process_elem(elem,
                 titleset: set,
                 ns: str,
                 lang: str,
                 pos: str,
                 optfilter: str):
	"""
	Parse and extract page titles, depending on given arguments.

	Currently adapted for ruwiktionary, other langs will follow.
	"""
	if elem.getparent().tag == (ns+'page'):
		has_ns0 = False
		has_lang = False
		has_pos = False
		has_optfilter = False

		pos_pattern = re.compile('{{'+pos+'.'+lang)
		opt_pattern = re.compile(optfilter)

		for sib in etree.SiblingsIterator(elem, tag=('{*}ns')):
			if sib.text == '0':
				has_ns0 = True
				break

		for sib in etree.SiblingsIterator(elem, tag=('{*}revision')):
			for sibchild in etree.ElementChildIterator(sib, tag='{*}text'):
				if type(sibchild.text) == str:
					# language string: either empty or, e.g., '= {{-ru-}} ='
					if not lang \
					   or '= {{-'+lang+'-}} =' in sibchild.text:
						has_lang = True
					# pos string: either empty or, e.g., '{{сущ ru' or '{{сущ-ru'
					if not pos \
					   or re.search(pos_pattern, sibchild.text):
						has_pos = True
					# optional additional regex string to search page text for
					if not optfilter \
					   or re.search(opt_pattern, sibchild.text):
						has_optfilter = True

		if elem.tag == (ns+'title') \
		   and elem.text \
		   and has_ns0 \
		   and has_lang \
		   and has_pos \
		   and has_optfilter:
			titleset.add(elem.text)

# ============================================================================ #


def main() -> int:

	print()
	print('   //  ___  ___ __   __  \\\\')
	print('  //    \\\\   \\\\ /    /    \\\\')
	print(' //      \\\\   \\\\    /      \\\\')
	print(' \\\\       \\\\  /\\\\  /       //')
	print('  \\\\       \\\\/  \\\\/       //')
	print('   \\\\  w  i  k  t  i  o  //')
	print()
	print('Memory-efficient word extractor from Wiktionary XML dumps')
	print()

	parser = argparse.ArgumentParser()
	parser.add_argument('infile',
	                    type=argparse.FileType('rb'),
	                    default=(None if sys.stdin.isatty() else sys.stdin),
	                    help="Wiktionary XML dump file (bz2-compressed), e.g., \
	                          'ruwiktionary-latest-pages-articles.xml.bz2'")
	parser.add_argument('outfile',
	                    nargs='?',
	                    type=argparse.FileType('w'),
	                    default=sys.stdout,
	                    help="list of page titles (plain text)")
	parser.add_argument('-l', '--lang',
	                    type=str,
	                    default='',
	                    help="filter by language, e.g., 'ru', 'en'")
	parser.add_argument('-p', '--pos',
	                    type=str,
	                    default='',
	                    help="filter by part of speech, \
	                          e.g., 'сущ', 'гл', 'adv' (sic), 'прил'")
	parser.add_argument('-r', '--regex',
	                    type=str,
	                    default='',
	                    help="optional additional regex string to filter page text by")

	args = parser.parse_args(args=None if sys.argv[1:] else ['--help'])

	titleset = set()
	ns = '{http://www.mediawiki.org/xml/export-0.10/}'

	with BZ2File(args.infile) as f:
		try:
			print('Loading XML document and creating XML tree object...')
			context = etree.iterparse(f, events=('end',), tag=ns+'title')
			print('Done.')
			print('Parsing XML tree...')
			fast_iter(context,
			          process_elem,
			          titleset,
			          ns,
			          args.lang,
			          args.pos,
			          args.regex)

		except etree.ParseError:
			print('Unexpected end of XML document, or malformed XML. Aborting...')

	print('Done.')
	print('Exporting wordlist into a plaintext file...')

	with args.outfile as f:
		for w in sorted(titleset):
			print(w, file=f)

	print('Done.')

	return 0

# ============================================================================ #


if __name__ == '__main__':
	sys.exit(main())
