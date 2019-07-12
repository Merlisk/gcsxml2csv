# Currently only DFRPG stuff, should be reasonably easy to expand to others

import sys
import csv
import uuid
import argparse
import xml.etree.ElementTree as ET
import collections
import warnings

DEFAULT_CSV_DELIMITER = ";"
DEFAULT_CSV_SUB_DELIMITER = ":"


# collections.Counter doesn't allow to save the structure as well
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



class CSV_FileWriter():
	def __init__(self, args):
		self.args = args
	
	# Probably remove after advantages (& equipment?) working
	def multiply_print_rows(self, row_dict, field_writer, ignore_fields, sep_char=','):
		list_of_multiples = []
		for field in row_dict:
			if not isinstance(row_dict[field], str):
				continue
			if row_dict[field].find(sep_char) > -1 and field not in ignore_fields:
				list_of_multiples.append(field)
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
	
	def print_csv_rows(self, rows, title_row, fieldnames):
		ordered_rows = collections.OrderedDict(sorted(rows.items()))
		title_writer = csv.writer(sys.stdout, delimiter=self.args['csv_delimiter'])
		title_writer.writerow(title_row)
		field_writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames, delimiter=self.args['csv_delimiter'])
		for rowname, row in ordered_rows.items():
			if self.args['remove_secondary_key_output'] and rowname.endswith(row[self.args['secondary_key_field']]):
				row[fieldnames[0]] = rowname.partition(self.args['csv_sub_delimiter'])[0]
			else:
				row[fieldnames[0]] = rowname
			field_writer.writerow(row)
			#if self.args.normalize and not already_normalized:
			#	self.multiply_print_rows(row, field_writer, ignore_fields)
			#else:
			#	field_writer.writerow(row)


class GCS_FileParser():
	def __init__(self, args):
		self.args = args
		self.xml_data = None
		self.current_element = None
		self.all_rows = {}
		self.current_row = {}
		self.multiple_same_names = []
		self.secondary_key_field = ""
		self.no_child_specifics = False
		self.csd = args.csv_sub_delimiter
		self.auto_clean_sub_fields = []
		self.read_xml_file()
		# super().__init__()
		# self.default_tags = ["ref"]  # see _got_default_child_text()
		# self.csv_titles_long = ["Page Reference"]
		# self.csv_titles_short = ["Ref"]
		# self.csv_fields = ["ref"]
	
	def read_xml_file(self):
		tree = ET.parse(self.args.input_filename)
		self.xml_data = tree.getroot()
	
	def choose_partial_parse(self):
		raise NotImplementederror("Called choose_partial_parse improperly.")
	
	def add_child_specfic_to_row(self, child, name):
		# if child.tag == "name":
		#	self.current_row["name"] = child.text
		# elif child.tag ==  :
		self.no_child_specifics = True
	
	def get_child_texts(self, xml_elem, sep=","):
		childs_text = ""
		for child in xml_elem:
			childs_text += child.text + sep
		if len(sep) > 0:
			childs_text = childs_text[:len(sep)*-1]
		return childs_text
	
	def _got_default_child_text(self, child):
		if child.tag in self.default_tags:
			self.current_row[child.tag] = child.text.strip()
			return True
		else:
			return False
	
	def _add_and_rename_rows_with_existing_name(self, name):
		if self.secondary_key_field not in self.current_row:
			raise RunTimeWarning("Secondary key field {} not found for name {}, row not saved.".format(self.secondary_key_field, name))
			return
		second_field = self.current_row[self.secondary_key_field]
		if not second_field:
			raise RunTimeWarning("Secondary key field {} for name {} was empty, row not saved.".format(second_field, name))
			return
		self.all_rows[name + self.csd + second_field] = self.current_row
		if name not in self.multiple_same_names:  # 2nd same name -> rename 1st
			second_field = self.all_rows[name][self.secondary_key_field]
			self.all_rows[name + self.csd + second_field] = self.all_rows[name]
			del self.all_rows[name]
	
	def post_row_actions(self):
		if self.auto_clean_sub_fields:
			for sub_field in self.auto_clean_sub_fields:
				if sub_field in self.current_row and self.current_row[sub_field]:
					self.current_row[sub_field] = self.current_row[sub_field][:-1]
		if self.current_row["name"]:
			name = self.current_row["name"]
			if name not in self.all_rows and name not in self.multiple_same_names:
				self.all_rows[name] = self.current_row
				return
			if self.args.same_name_action == 'first':
				pass
			elif self.args.same_name_action == 'last':
				self.all_rows[name] = self.current_row
			else:  # self.args.same_name_action == 'all'
				self._add_and_rename_rows_with_existing_name(name)
			self.multiple_same_names.append(name)
	
	def default_parse_all(self):
		for self.current_element in self.xml_data:
			self.current_row = { "name" : "" }
			for child in self.current_element:
				if self._got_default_child_text(child):
					continue
				self.add_child_specfic_to_row(child)
			self.post_row_actions()
	
	# If child classes need to change the parsing process, they can create 
	# their own parse-methods and/or call super().default_parse_all()
	def parse_all(self):
		self.default_parse_all()
		if self.no_child_specifics:
			print("No specific handling for child elements -- did everything work by defaults?")
	
	def parse(self):
		self.parse_all()


class DFRPG_skill_parser(GCS_FileParser):
	def __init__(self, args):
		super().__init__(args)
		self.default_tags = ["reference", "encumbrance_penalty_multiplier"]
		self.csv_titles_long = ["Skill name", "Attribute", "Difficulty", 
			"Specialization", "Page Reference", "Encumbrance Penalty"]
		self.csv_titles_short = ["Skill name", "Attr", "Diff", "Spec", "Ref", "EncPen"]
		self.csv_fields = ["name", "attr", "diff", "spec", "reference", "encumbrance_penalty_multiplier"]
	
	def add_child_specfic_to_row(self, child):
		if child.tag == "name":
			self.current_row["name"] = child.text
		elif child.tag == "difficulty":
			da = child.text.partition('/')
			self.current_row["attr"] = da[0]
			self.current_row["diff"] = da[2]
		elif child.tag == "specialization":
			text = child.text.strip()
			name = self.current_row["name"]
			if name in self.all_rows:
				if "spec" in self.all_rows[name]:
					self.all_rows[name]["spec"] += self.csd + child.text
				else:
					self.all_rows[name]["spec"] = child.text
				self.current_row["name"] = ""
			else:
				self.current_row["spec"] = child.text


class DFRPG_spell_parser(GCS_FileParser):
	# Notes on spells:
	# power_source is always arcane -> ignored
	LIST_SPELL_PREREQS = ["name", "college", "college_count", "quantity"]
	SECONDARY_KEY_FIELD = "caster_type"
	
	def __init__(self, args):
		super().__init__(args)
		self.secondary_key_field = self.SECONDARY_KEY_FIELD
		self.default_tags = ["spell_class", "casting_cost", 
			"maintenance_cost", "casting_time", "duration", "reference"]
		self.csv_titles_long = ["Spell name", "College", "Class", "Casting cost", 
			"Maintenance cost", "Casting time", "Duration", "Refence", 
			"Prerequisites", "Caster type"]
		self.csv_titles_short = ["Spell name", "College", "Class", "Cast cost", 
			"Maint cost", "Cast time", "Duration", "Ref", 
			"PreReq", "Caster type"]
		self.csv_fields = ["name", "college", "spell_class", "casting_cost", 
			"maintenance_cost", "casting_time", "duration", "reference", 
			"prereq", "caster_type"]
	
	def _get_spell_prereq_string(self, prereq_list):
		out_string = ""
		for prereq in prereq_list:
			if prereq.tag == "advantage_prereq":
				name_elem = prereq.find("name")
				name = name_elem.text if name_elem is not None else ""
				level_elem = prereq.find("level")
				level = level_elem.text if level_elem is not None else ""
				out_string += "advantage" + self.csd + name + self.csd + \
					level + self.csd
			elif prereq.tag == "spell_prereq":
				out_string += "spell" + self.csd
				for sp_prereq in self.LIST_SPELL_PREREQS:
					elem = prereq.find(sp_prereq)
					if elem is not None:
						out_string += sp_prereq + self.csd + elem.text + self.csd
			elif prereq.tag == "attribute_prereq":
				out_string += "attribute" + self.csd + \
					prereq.get("which") + self.csd + prereq.text + self.csd
			elif prereq.tag == "prereq_list":
				out_string += self._get_spell_prereq_string(prereq) + self.csd
		return out_string[:-1]
	
	def add_child_specfic_to_row(self, child):
		if child.tag == "name":
			self.current_row["name"] = child.text
		elif child.tag == "college":
			self.current_row["college"] = child.text
			if child.text == "Clerical" or child.text == "Druid":
				self.current_row["caster_type"] = child.text
			else:
				self.current_row["caster_type"] = "Wizardly"
		elif child.tag == "prereq_list":
			self.current_row["prereq"] = self._get_spell_prereq_string(child)
	
	def parse(self):
		self.xml_data = self.xml_data.findall(".//spell")
		self.parse_all()


class DFRPG_advantage_parser(GCS_FileParser):
	# Notes on advantages:
	# type doesn't exist in DFRPG, but included in the data for completeness' sake
	# cr (Self-control number) is always 12, but included to show which disadvantages use it
	DEFAULT_TAGS_ALWAYS_PRESENT = ["type", "reference"]
	DEFAULT_TAGS_SOMETIMES_PRESENT = ["base_points", "points_per_level", 
		"levels", "cr", "notes"]
	
	def __init__(self, args):
		super().__init__(args)
		# self.secondary_key_field = self.SECONDARY_KEY_FIELD
		self.auto_clean_sub_fields = ["modifiers", "categs", "skills"]
		self.default_tags = self.DEFAULT_TAGS_ALWAYS_PRESENT + self.DEFAULT_TAGS_SOMETIMES_PRESENT
		# todo: check long names, could any of them be more descriptive?
		self.csv_titles_long  = ["Advantage name", "Type", "Base point cost", 
			"Cost of points per level", "Levels", "Page Reference", 
			"Categories", "Prerequisites", "Self-control number", 
			"Modifiers", "Skills", "Notes"]
		self.csv_titles_short  = ["Advantage name", "Type", "Pts base", 
			"Pts/Lvl", "Lvls", "Ref", "Categories", "PreReqs", "SCN",
			"Skills", "Modifiers", "Notes"]
		self.csv_fields = ["name", "type", "base_points", 
			"points_per_level", "levels", "reference", "categs", "prereqs", "cr", 
			"skills", "modifiers", "notes"]
	
	def add_child_specfic_to_row(self, child):
		if child.tag == "name":
			self.current_row["name"] = child.text
		elif child.tag == "modifier":
			if "modifiers" not in self.current_row:
				self.current_row["modifiers"] = ""
			modifier_string = child.find('name').text + self.csd + \
				child.find('cost').text + self.csd
			self.current_row["modifiers"] += modifier_string
		elif child.tag == "categories":
			categories_string = ""
			for category_child in child:
				categories_string += category_child.text + self.csd
			self.current_row["categs"] = categories_string
		elif child.tag == "prereq_list":
			self.current_row["prereqs"] = True
		elif child.tag == "skill_bonus":
			if "skills" not in self.current_row:
				self.current_row["skills"] = ""
			# NoneType won't convert to string
			specialization_text = child.find('specialization').text + self.csd if child.find('specialization').text else ""
			skill_string = child.find('name').text + self.csd + \
				specialization_text + child.find('amount').text + self.csd
			self.current_row["skills"] += skill_string
	
	def parse(self):
		self.parse_all()
		# Hackety hax due to xml form
		self.all_rows["Language_note"] = {"name":"Language_note", "notes": "Costs depend on Language Talent" }
		self.all_rows["Wealth_second"] = {"name":"Wealth_second", "notes": "There are two Wealth advantages, check which one you're missing" }


# Old Advantages code
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
	swu = {}
	for child in weap:
		if child.tag == "usage":
			usage = child.text
		elif child.tag in default_eqp_tags:
			swu[child.tag] = child.text
	return usage, swu
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
			# Problems -- we need to create multiple rows for same weapon depending on usage
			usage, swu = parse_weapon_tags(child, se)
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



def create_parameters():
	FILE_TYPE_CHOICES = ['all_tags', 'skills', 'spells', 'equipment', 'advantages']
	SAME_NAME_CHOICES = ['first', 'last', 'all']
	arg_parser = argparse.ArgumentParser(description="Read a Gurps character sheet XML data file and output to csv.",
		epilog="Currently prints to stdout, pipe it to whatever file you want to or just admire it on your console.")
	arg_parser.add_argument('-i', '--input_filename', action='store', required=True)
	arg_parser.add_argument('-t', '--input_file_type', action='store', required=True,
		choices=FILE_TYPE_CHOICES,
		help="'all_tags' will display an indented tree-list of all tags in the xml file, with amounts.")
	arg_parser.add_argument('-ut', '--all_tags_unused_tag_name', action='store', default='Number', 
		help="Used with all_tags; a tag name unused in the XML file, used for counting number of tags.")
	arg_parser.add_argument('-sn', '--same_name_action', action='store', 
		choices=SAME_NAME_CHOICES, default='first',
		help="Which to keep when multiple rows would have same name.  All means using a secondary key field when same names exist.")
	arg_parser.add_argument('-sr', '--remove_secondary_key_output', action='store_true', 
		help="When printing output, remove the secndary key field from the name.")
	arg_parser.add_argument('-cd', '--csv_delimiter', action='store', default=DEFAULT_CSV_DELIMITER,
		help="Character to use as csv delimiter.")
	arg_parser.add_argument('-cs', '--csv_sub_delimiter', action='store', default=DEFAULT_CSV_SUB_DELIMITER,
		help="Character to use as a subfield csv delimiter when storing irregular data.")
	#arg_parser.add_argument('-', '--', action='store', choices=['', '', ''], help="Used with")
	return arg_parser

def create_print_out_args(args, parser):
	out_dict = {}
	out_dict['csv_delimiter'] = args.csv_delimiter
	out_dict['csv_sub_delimiter'] = args.csv_sub_delimiter
	out_dict['remove_secondary_key_output'] = args.remove_secondary_key_output
	out_dict['secondary_key_field'] = parser.secondary_key_field
	return out_dict


def main():
	arg_parser = create_parameters()
	args = arg_parser.parse_args()
	xml_type = args.input_file_type
	if xml_type == 'all_tags':
		root = ET.parse(args.input_filename).getroot()
		tags_dict = { args.all_tags_unused_tag_name: 1 }
		find_all_elements(root, tags_dict, args.all_tags_unused_tag_name)
		print_tags_dict(tags_dict, "", root.tag, args.all_tags_unused_tag_name)
		return
	elif xml_type == 'skills':
		xml_parser = DFRPG_skill_parser(args)
	elif xml_type == 'spells':
		xml_parser = DFRPG_spell_parser(args)
	elif xml_type == 'advantages':
		xml_parser = DFRPG_advantage_parser(args)
	elif xml_type == 'equipment':
		#xml_parser = DFRPG_equipment_parser(args)
		print("Sorry, equipment hasn't been implemented yet.")
		return
		# eqp, eqp_titles, eqp_fields = parse_DFRPG_equipment(root)
		# print_csv_rows(eqp, eqp_titles, eqp_fields)
	else:
		raise RuntimeError("Somehow got unknown file type through argparse!")
	xml_parser.parse()
	out_args = create_print_out_args(args, xml_parser)
	csv_writer = CSV_FileWriter(out_args)
	csv_writer.print_csv_rows(xml_parser.all_rows, xml_parser.csv_titles_short, xml_parser.csv_fields)

if __name__ == "__main__":
	main()

