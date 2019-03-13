# Currently only DFRPG stuff, should be reasonably easy to expand to others

import sys
import csv
import argparse
import xml.etree.ElementTree as ET
import collections


args = None

def find_all_elements(elem, tags_dict, unused_tag_name):
	if not isinstance(elem, int):
		for child in elem:
			if child.tag in tags_dict:
				sub_dict = tags_dict[child.tag]
				sub_dict[unused_tag_name] += 1
			else: 
				sub_dict = { unused_tag_name: 1 }
			child_tag, child_val = find_all_elements(child, sub_dict, unused_tag_name)
			if child_tag not in tags_dict:
				tags_dict[child_tag] = child_val
	return elem.tag, tags_dict

def print_tags_dict(tags_dict, depth, tag, unused_tag_name):
	if not isinstance(tags_dict, int):
		print(depth + tag + ': ' + str(tags_dict[unused_tag_name]))
		for child in tags_dict:
			print_tags_dict(tags_dict[child], depth + '  ', child, unused_tag_name)


def parse_DFRPG_skills(root):
	# Maybe use global args and args.group_similar for specialties?	
	skill_titles = ["Skill name", "Attr", "Diff", "Ref", "EncPen"]
	skill_fields = ["skillname", "attr", "diff", "ref", "enc_pen"]
	skills = {}
	# specialties = {}
	for skill in root:
		# unique = True
		name = ""
		ss = {}  # single skill
		for child in skill:
			if child.tag == "name":
				name = child.text
				if name in skills:
					continue  # unique = False
			elif child.tag == "difficulty":
				da = child.text.partition('/')
				ss["attr"] = da[0]
				ss["diff"] = da[2]
			elif child.tag == "reference":
				ss["ref"] = child.text
			elif child.tag == "encumbrance_penalty_multiplier":
				ss["enc_pen"] = child.text
			# elif child.tag == "specialization":
			# 	ss[""] = child.text
		if name:
			skills[name] = ss
	return skills, skill_titles, skill_fields


def parse_DFRPG_single_spell(spell):
	if spell.tag != "spell":
		return None, None
	name = ""
	ss = {}  # single spell
	for child in spell:
		if child.tag == "name":
			name = child.text
		elif child.tag == "college":
			ss["coll"] = child.text
		elif child.tag == "spell_class":
			ss["class"] = child.text
		elif child.tag == "casting_cost":
			ss["ccost"] = child.text
		elif child.tag == "maintenance_cost":
			ss["mcost"] = child.text
		elif child.tag == "casting_time":
			ss["ctime"] = child.text
		elif child.tag == "duration":
			ss["dur"] = child.text
		elif child.tag == "reference":
			ss["ref"] = child.text
	return name, ss

def add_spell_to_all_spells(name, new_spell, spells, caster_type):
	global args
	# Single entries, but NOTE: Cleric and Druid pinv_req not always equal!
	if args.group_similar:
		if name in spells:
			spells[name]["caster_type"] += ", " + caster_type
			spells[name]["coll"] = new_spell["coll"]
		else:
			new_spell["caster_type"] = caster_type
			spells[name] = new_spell
	else:  # Individual entry for each similar spell
		new_spell["caster_type"] = caster_type
		if name in spells:
			if "caster_type" in spells[name]:
				old_one_rename = name + "--" + spells[name]["caster_type"]
				spells[old_one_rename] = spells[name].copy()
				spells[name] = {}
			new_name = name + "--" + caster_type
			spells[new_name] = new_spell
		else:
			spells[name] = new_spell

def add_spell_cont(spell_cont, spells, caster_type):
	pinv_req = 0  # Power investiture requirement
	for spell in spell_cont:
		if spell.tag == "notes":
			pinv_req = int(spell.text)
		if spell.tag != "spell":
			continue
		name, new_spell = parse_DFRPG_single_spell(spell)
		if pinv_req > 0:
			new_spell["req"] = pinv_req
		add_spell_to_all_spells(name, new_spell, spells, caster_type)

def parse_DFRPG_spells(root):
	spell_titles = ["Spell name", "College", "Class", "Cast cost", "Maint cost", "Cast time", "Duration", "Ref", "Req", "Caster type"]
	spell_fields = ["spellname", "coll", "class", "ccost", "mcost", "ctime", "dur", "ref", "req", "caster_type"]
	all_spells = {}
	for sp_cont in root:
		caster_type = sp_cont.find('name').text
		if caster_type == "Clerical" or caster_type == "Druidic":
			for cont in sp_cont:
				add_spell_cont(cont, all_spells, caster_type)
		elif caster_type == 'Wizardly':
			add_spell_cont(sp_cont, all_spells, caster_type)
		else:
			print('Unknown caster type {}, not saving anything.'.format(caster_type))
	return all_spells, spell_titles, spell_fields


def parse_DFRPG_equipment(root):
	print("Sorry, equipment parsing hasn't been implemented yet.")
	return None, None, None


def parse_DFRPG_advantages(root):
	print("Sorry, advantages parsing hasn't been implemented yet.")
	return None, None, None


def print_csv_rows(rows, title_row, fieldnames):
	ordered_rows = collections.OrderedDict(sorted(rows.items()))
	title_writer = csv.writer(sys.stdout, delimiter=';')
	title_writer.writerow(title_row)
	field_writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames, delimiter=';')
	for rowname, row in ordered_rows.items():
		row[fieldnames[0]] = rowname
		field_writer.writerow(row)


def create_parameters():
	arg_parser = argparse.ArgumentParser(description="Read a Gurps character sheet XML data file and output to csv.",
		epilog="Currently prints to stdout, pipe it to whatever file you want to or just admire it on your console.")
	arg_parser.add_argument('-i', '--input_filename', action='store', required=True)
	arg_parser.add_argument('-t', '--input_file_type', action='store', required=True,
		choices=['all_tags', 'skills', 'spells', 'equipment', 'advantages'],
		help="'all_tags' will display an indented tree-list of all tags in the xml file, with amounts.")
	arg_parser.add_argument('-u', '--unused_tag_name', action='store', default='Number', help="A tag name unused in the XML file; for counting number of tags with the 'all_tags' file type.")
	arg_parser.add_argument('--group_similar', action='store_true', help="Merge multiple very similar items in to a single row.")
	# arg_parser.add_argument('-c', '--container_category', action='store', help="Only get contents in a container with this category.")
	return arg_parser


def main():
	arg_parser = create_parameters()
	global args
	args = arg_parser.parse_args()
	tree = ET.parse(args.input_filename)
	root = tree.getroot()
	xml_type = args.input_file_type
	if xml_type == 'all_tags':
		tags_dict = { args.unused_tag_name: 1 }
		find_all_elements(root, tags_dict, args.unused_tag_name)
		print_tags_dict(tags_dict, "", root.tag, args.unused_tag_name)
	elif xml_type == 'skills':
		skills, skill_titles, skill_fields = parse_DFRPG_skills(root)
		print_csv_rows(skills, skill_titles, skill_fields)
	elif xml_type == 'spells':
		spells, spell_titles, spell_fields = parse_DFRPG_spells(root)
		print_csv_rows(spells, spell_titles, spell_fields)
	elif xml_type == 'equipment':
		eqp, eqp_titles, eqp_fields = parse_DFRPG_equipment(root)
		#print_csv_rows(eqp, eqp_titles, eqp_fields)
	elif xml_type == 'advantages':
		advs, adv_titles, adv_fields = parse_DFRPG_advantages(root)
		#print_csv_rows(advs, adv_titles, adv_fields)
	else:
		raise RuntimeError("Somehow got unknown file type through argparse!")


if __name__ == "__main__":
	main()
