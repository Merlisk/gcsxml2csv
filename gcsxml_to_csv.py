# Currently only DFRPG stuff, should be reasonably easy to expand to others

import sys
import csv
import uuid
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


def get_child_texts(xml_obj, sep=","):
	childs_text = ""
	for child in xml_obj:
		childs_text += child.text + sep
	if len(sep) > 0:
		childs_text = childs_text[:len(sep)*-1]
	return childs_text


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
	default_spell_tags = ["college", "spell_class", "casting_cost", 
		"maintenance_cost", "casting_time", "duration", "reference"]
	if spell.tag != "spell":
		return None, None
	name = ""
	single_spell = {}
	for child in spell:
		if child.tag == "name":
			name = child.text
		elif child.tag in default_spell_tags:
			single_spell[child.tag] = child.text
	return name, single_spell

def add_spell_to_all_spells(name, new_spell, spells, caster_type):
	global args
	# Individual entry for each similar spell
	if args.normalize:
		if name in spells:
			if "caster_type" in spells[name]:
				old_one_rename = name + " [" + spells[name]["caster_type"] + "]"
				spells[old_one_rename] = spells[name].copy()
			new_name = name + " [" + caster_type + "]"
			spells[new_name] = new_spell
		else:
			spells[name] = new_spell
	# Single entries, but NOTE: Cleric and Druid pinv_req not always equal!
	else:
		if name in spells:
			spells[name]["caster_type"] += ", " + caster_type
			spells[name]["college"] = new_spell["college"]
		else:
			new_spell["caster_type"] = caster_type
			spells[name] = new_spell
		new_spell["caster_type"] = caster_type

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
	spell_titles = ["Spell name", "College", "Class", "Cast cost", 
		"Maint cost", "Cast time", "Duration", "Ref", 
		"Req", "Caster type"]
	spell_fields = ["spellname", "college", "spell_class", "casting_cost", 
		"maintenance_cost", "casting_time", "duration", "reference", 
		"req", "caster_type"]
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

def add_DFRPG_adv_skill(adv, skill):
	skill_spec = skill.find('specialization').text if skill.find('specialization').text else ""
	skill_data = skill.find('name').text + ":" + skill_spec + ":" + skill.find('amount').text
	if "skills" in adv:
		adv["skills"] += "," + skill_data
	else:
		adv["skills"] = skill_data

def add_DFRPG_adv(adv, all_abil, ability):
	default_adv_tags = ["base_points", "points_per_level", "levels", 
		"notes", "cr", "reference"]
	category_abbr = { "Advantage": "Adv", "Disadvantage": "DisAdv", 
		"Perk": "Perk", "Quirk": "Quirk", 
		"Attribute": "Attr", "Cinematic": "Cinem", 
		"Language": "Lang", "Power": "Power", "Talent": "Tal" }
	if adv.tag != "advantage":
		return
	name = ""
	sa = {}  # single advantage
	for child in adv:
		if child.tag == "name":
			name = child.text
		elif child.tag in default_adv_tags:
			sa[child.tag] = child.text
		elif child.tag == "prereq_list":
			sa["prereqs"] = True
		elif child.tag == "modifier":
			mod_name = child.find('name').text
			if "modifiers" in sa:
				sa["modifiers"] += ", " + mod_name
			else:
				sa["modifiers"] = mod_name
		elif child.tag == "categories":
			cat_text = ""
			for cat_child in child:
				cat_text += category_abbr[cat_child.text] + ","
			sa["categs"] = cat_text[:-1]
		elif child.tag == "skill_bonus":
			add_DFRPG_adv_skill(sa, child)
	if ability:
		sa["ability"] = ability
	if name not in all_abil:
		all_abil[name] = sa
	else:
		all_abil[name + "_" + str(uuid.uuid4())] = sa

def parse_DFRPG_advantages(root):
	adv_titles = ["Advantage name", "Pts base", "Pts/Lvl", "Lvls", 
		"Ref", "Categories", "PreReqs", "Modifiers", "SCN", "Skills", 
		"Ability", "Notes"]
	adv_fields = ["advname", "base_points", "points_per_level", "levels", 
		"reference", "categs", "prereqs", "modifiers", "cr", "skills", 
		"ability", "notes"]
	all_advs = {}
	for adv in root:
		if adv.tag == "advantage_container":
			ability = adv.find('name').text.split()[0]
			for actual_adv in adv:
				add_DFRPG_adv(actual_adv, all_advs, ability)
		else:
			add_DFRPG_adv(adv, all_advs, "")
	return all_advs, adv_titles, adv_fields


def parse_weapon_tags(weap, se):
	default_weap_tags = ["strength", "reach", "parry",
		"accuracy", "range", "bulk", "shots"]
	weap_titles = ["Str Req", "Reach", "Parry", 
		"Acc", "Range", "Bulk", "Shots", 
		"Base Att", "Dam Bonus", "Dam type", "Usages", "Skill"]
	weap_fields = ["strength", "reach", "parry", 
		"accuracy", "range", "bulk", "shots", 
		"att_type", "dam_bonus", "dam_type", "usage", "main_skill"]
	#, "", "", "", "", "", ""
	pass
	#    melee_weapon: 217 # same item can have multiples -> separate csv
	#      damage: 217 -> separate "value type", value -> [sw|thr](bonus)
	## if begins with [sw|thr], try, otherwise extras +=
	## from last space to end -> damage type (check)
	## between beginning and end, remove spaces, if True -> dam_bonus
	## damage_types = ["cr", "cut", "imp", "pi", "pi-", "cor"]
	#      usage: 201; str, add to name
	#      block: 217 # can ignore, (almost) always No for weapons
	#      default: 1204 # If
	#        type: 1204 # is Skill
	#        modifier: 1204 # is 0 (others are defaults and < 0 )
	#        name: 989 # then save
	#        specialization: 21 # add if above?
	#    ranged_weapon: 57
	#      damage: 57
	#      usage: 49
	#      rate_of_fire: 43  # mostly useless. either 1 or None (grenades)
	#      default: 140 # Same as melee weapon


def add_shield_bonus(attrib_bonii, se):
	req_to_be_def_bonus = ["block", "dodge", "parry"]
	attribs = []
	common_bonus = None
	all_bonus_same = True
	for attr, amount in attrib_bonii.items():
		if common_bonus is None:
			common_bonus = amount
		elif common_bonus != amount:
			all_bonus_same = False
		attribs.append(attr)
	if all_bonus_same and sorted(attribs) == req_to_be_def_bonus:
		se["def_bonus"] = common_bonus

def parse_single_equipment(eqp):
	default_eqp_tags = ["value", "weight", "notes", "reference"]
	se = {} # single_equipment
	attrib_bonii = {}
	for child in eqp:
		if child.tag == "description":
			name = child.text
		elif child.tag in default_eqp_tags:
			se[child.tag] = child.text
		elif child.tag == "categories":
			se["categs"] = get_child_texts(child)
		elif child.tag == "melee_weapon" or child.tag == "ranged_weapon":
			parse_weapon_tags(child, se)
		elif child.tag == "attribute_bonus":  # Shields
			attr = child.find("attribute").text
			amount = child.find("amount").text
			attrib_bonii[attr] = amount
	#	elif child.tag == "":
	#		se[""] = child.text
	if attrib_bonii:
		add_shield_bonus(attrib_bonii, se)
	return name, se

def parse_single_armor_piece(arm):
	default_armor_tags = ["value", "weight", "notes", "reference"]
	common_dr_bonus = None
	all_dr_bonus_same = True
	dr_bonii = {}
	sap = {}  # Single armor piece
	for child in arm:
		if child.tag == "description":
			name = child.text
		elif child.tag in default_armor_tags:
			sap[child.tag] = child.text
		elif child.tag == "categories":
			sap["categs"] = get_child_texts(child)
		elif child.tag == "dr_bonus":
			dr = int(child.find("amount").text)
			loc = child.find("location").text
			dr_bonii[loc] = dr
			if common_dr_bonus is None:
				common_dr_bonus = dr
			elif common_dr_bonus != dr:
				all_dr_bonus_same = False
	if "notes" not in sap:
		sap["notes"] = ""
	locs = ""
	if all_dr_bonus_same:
		sap["dr_bonus"] = str(common_dr_bonus)
		for loc in dr_bonii:
			locs += loc + ", "
	else:
		sap["dr_bonus"] = ""
		for loc in dr_bonii:
			locs += loc + ":" + str(dr_bonii[loc]) + ", "
	locs = locs[:-2]
	sap["body_locations"] = locs
	return name, sap

def parse_armor_container(eqp):
	armor_titles = ["DR", "Location", "Armor suit"]
	armor_fields = ["dr_bonus", "body_locations", "part_of_armor_suit"]
	arm_dict = {}
	whole_suit = {}
	total_value = 0
	total_weight = 0
	common_dr_bonus = None
	all_dr_bonus_same = True
	common_notes = None
	different_notes = ""
	locations = ""
	for child in eqp:
		if child.tag == "description":
			name = child.text
		elif child.tag == "reference":
			whole_suit["reference"] = child.text
		elif child.tag == "categories":
			whole_suit["categs"] = get_child_texts(child)
		elif child.tag == "equipment":
			child_name, sap = parse_single_armor_piece(child)
			if not child_name.endswith("(Full Face)"):
				total_value += int(sap["value"])
				total_weight += float(sap["weight"].split()[0])
			sap["part_of_armor_suit"] = name
			arm_dict[child_name] = sap
			# Collate info from different armor parts
			locations += sap["body_locations"] + ", "
			notes = sap["notes"]
			if common_dr_bonus is None:
				common_dr_bonus = sap["dr_bonus"]
			elif common_dr_bonus != sap["dr_bonus"]:
				all_dr_bonus_same = False
			if common_notes is None:
				common_notes = notes
			elif common_notes != notes:
				different_notes += notes + ", "
	whole_suit["body_locations"] = locations[:-2]
	# whole_suit["dr_bonus"] = common_dr_bonus if all_dr_bonus_same else "[This suit had different DR bonii]"
	if all_dr_bonus_same:
		whole_suit["dr_bonus"] = common_dr_bonus
	else:
		whole_suit["dr_bonus"] = "[This suit had different DR bonii]"
	# whole_suit["notes"] = "[Warning, got different notes from armor pieces!]: " + different_notes[:-2] if different_notes else common_notes
	if different_notes:
		whole_suit["notes"] = "[Warning, got different notes from armor pieces!]: " + different_notes[:-2]
	else:
		whole_suit["notes"] = common_notes
	whole_suit["value"] = str(total_value)
	whole_suit["weight"] = str(total_weight) + " lb"
	arm_dict[name] = whole_suit
	return arm_dict

def parse_DFRPG_equipment(root):
	eq_titles = ["Equipment name", "Cost", "Weight", "Ref", 
		"Can carry", "Def bonus", 
		"DR", "Location", "Armor suit", 
		"Categories", "Notes"]
	eq_fields = ["eqname", "value", "weight", "reference", 
		"carry_weight", "def_bonus", 
		"dr_bonus", "body_locations", "part_of_armor_suit", 
		"categs", "notes"]
	#, "", "", "", "", "", ""
	all_eqs = {}
	for eqp in root:
		if eqp.tag == "equipment_container":
			categs = eqp.find("categories")
			if categs.find("category").text == "Armor":
				arm_dict = parse_armor_container(eqp)
				all_eqs.update(arm_dict)
				continue
			else:
				name, se = parse_single_equipment(eqp)
				prl = eqp.find("prereq_list")
				if prl:
					se["carry_weight"] = prl.find("contained_weight_prereq").text
		else:
			name, se = parse_single_equipment(eqp)
		all_eqs[name] = se
	return all_eqs, eq_titles, eq_fields


def multiply_print_rows(row_dict, field_writer, ignore_fields, sep_char=','):
	list_of_multiples = []
	for field in row_dict:
		if not isinstance(row_dict[field], str):
			continue
		if row_dict[field].find(sep_char) > -1 and field not in ignore_fields:
			list_of_multiples.append(field)
	#print("Debug: ", list_of_multiples)
	if len(list_of_multiples) == 0:
		field_writer.writerow(row_dict)
	elif len(list_of_multiples) > 1:
		print("Warning, had multiple divisible fields, left next row alone!;")
		field_writer.writerow(row_dict)
	else:  # len(list_of_multiples) == 1
		sub_rows = row_dict[list_of_multiples[0]].split(sep_char)
		temp_row = row_dict.copy()
		for sub_row in sub_rows:
			temp_row[list_of_multiples[0]] = sub_row.strip()
			field_writer.writerow(temp_row)

def print_csv_rows(rows, title_row, fieldnames, ignore_fields=[], already_normalized=False):
	global args
	ordered_rows = collections.OrderedDict(sorted(rows.items()))
	title_writer = csv.writer(sys.stdout, delimiter=';')
	title_writer.writerow(title_row)
	field_writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames, delimiter=';')
	for rowname, row in ordered_rows.items():
		row[fieldnames[0]] = rowname
		if args.normalize and not already_normalized:
			multiply_print_rows(row, field_writer, ignore_fields)
		else:
			field_writer.writerow(row)


def create_parameters():
	arg_parser = argparse.ArgumentParser(description="Read a Gurps character sheet XML data file and output to csv.",
		epilog="Currently prints to stdout, pipe it to whatever file you want to or just admire it on your console.")
	arg_parser.add_argument('-i', '--input_filename', action='store', required=True)
	arg_parser.add_argument('-t', '--input_file_type', action='store', required=True,
		choices=['all_tags', 'skills', 'spells', 'equipment', 'advantages'],
		help="'all_tags' will display an indented tree-list of all tags in the xml file, with amounts.")
	arg_parser.add_argument('-u', '--unused_tag_name', action='store', default='Number', help="A tag name unused in the XML file; for counting number of tags with the 'all_tags' file type.")
	arg_parser.add_argument('-n', '--normalize', action='store_true', help="Create separate rows from items in a single field.")
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
		print_csv_rows(spells, spell_titles, spell_fields, already_normalized=True)
	elif xml_type == 'advantages':
		advs, adv_titles, adv_fields = parse_DFRPG_advantages(root)
		print_csv_rows(advs, adv_titles, adv_fields, ignore_fields=["categs"])
	elif xml_type == 'equipment':
		eqp, eqp_titles, eqp_fields = parse_DFRPG_equipment(root)
		print_csv_rows(eqp, eqp_titles, eqp_fields)
	else:
		raise RuntimeError("Somehow got unknown file type through argparse!")


if __name__ == "__main__":
	main()
