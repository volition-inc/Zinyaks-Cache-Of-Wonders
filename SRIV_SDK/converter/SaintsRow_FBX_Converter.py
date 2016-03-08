"""
Volition FBX Converter

Import an FBX file
- Convert to Saints Row Files
-- Character Mesh ( *.cmeshx )
-- Skeleton File  ( *.rigx )
-- Material Library ( *.matlibx )
Version - 1.05
Force 3dsmax Setting will take originating fbx files from 3dsmax, Exported from maya and convert without any user end rotation modifications.
The main mesh must have a -90 degree rotation on the X axis
"""

import os
import sys
import struct
import xml.dom.minidom
import xml.etree.cElementTree
import wx
import wx.grid as gridlib
import wx.lib.agw.pyprogress
import subprocess
import stat
import time
import json
import webbrowser
import shutil
import ctypes
import ctypes.wintypes
import copy

import FbxCommon

# Debug Print Flags
DEBUG_VERTS = False
DEBUG_WEIGHTS = False
DEBUG_OUTPUT = False
DEBUG_BONE_OUTPUT = False
DEBUG_MATERIAL = False
DEBUG_BLENDSHAPES = False

# Globals
WORKING_DIR = None
SMALL_LARGE_TEXTURES = { }

# Crunchers
PEG_CRUNCHER = 'peg_assemble_wd'
RIG_CRUNCHER = 'rig_cruncher_wd'
MAT_CRUNCHER = 'material_library_crunch_wd'
MESH_CRUNCHER = 'mesh_crunch_wd'
TEXTURE_CRUNCHER = 'texture_crunch_wd'
MORPH_CRUNCHER = 'morph_crunch_wd'
CRUNCHERS = [ PEG_CRUNCHER, RIG_CRUNCHER, MAT_CRUNCHER, MESH_CRUNCHER, TEXTURE_CRUNCHER, MORPH_CRUNCHER ]

# Conversion Values
COORD_SYS_TRANSFORM = None
MAX_SCALE_VALUE = 39.3701
MAYA_SCALE_VALUE = 100
IN_TO_METERS = 0.0254
CM_TO_METERS = 0.01

IS_3DSMAX = False
IS_MAYAYUP = False
SCALE_VALUE = MAX_SCALE_VALUE
SCENE_SCALE_CONVERSION = 0.01

BLENDSHAPE_NAMES = { 'body_gender_female' : 'body gender female',
                     'body_gender_male' : 'body gender male',
                     'body_fat_plus' : 'body fat +',
                     'body_fat_minus' : 'body fat -',
                     'body_muscle' : 'body muscle' }

# Bone Name Mappings
BONE_NAMES = { 'bone_l_thigh' : 'bone_l-thigh',
               'bone_l_calf' : 'bone_l-calf',
               'bone_l_calftwist1' : 'bone_l-calftwist1',
               'bone_l_foot' : 'bone_l-foot',
               'bone_l_toe0' : 'bone_l-toe0',
               'bone_l_knee' : 'bone_l-knee',
               'bone_l_thightwist1' : 'bone_l-thightwist1',
               'bone_r_thigh' : 'bone_r-thigh',
               'bone_r_calf' : 'bone_r-calf',
               'bone_r_calftwist1' : 'bone_r-calftwist1',
               'bone_r_foot' : 'bone_r-foot',
               'bone_r_toe0' : 'bone_r-toe0',
               'bone_r_knee' : 'bone_r-knee',
               'bone_r_thightwist1' : 'bone_r-thightwist1',
               'bone_l_clavicle' : 'bone_l-clavicle',
               'bone_l_upperarmtwist1' : 'bone_l-upperarmtwist1',
               'bone_l_foretwist' : 'bone_l-foretwist',
               'bone_l_elbow' : 'bone_l-elbow',
               'bone_l_foretwist1' : 'bone_l-foretwist1',
               'bone_l_hand' : 'bone_l-hand',
               'bone_l_finger1' : 'bone_l-finger1',
               'bone_l_finger11' : 'bone_l-finger11',
               'bone_l_finger2' : 'bone_l-finger2',
               'bone_l_finger21' : 'bone_l-finger21',
               'bone_l_finger3' : 'bone_l-finger3',
               'bone_l_finger31' : 'bone_l-finger31',
               'bone_l_finger4' : 'bone_l-finger4',
               'bone_l_finger41' : 'bone_l-finger41',
               'bone_l_handprop' : 'bone_l-handprop',
               'bone_l_thumb1' : 'bone_l-thumb1',
               'bone_l_thumb11' : 'bone_l-thumb11',
               'bone_l_upperarmtwist2' : 'bone_l-upperarmtwist2',
               'bone_l_upperarmtwist3' : 'bone_l-upperarmtwist3',
               'bone_l_eye' : 'bone_l-eye',
               'bone_r_eye' : 'bone_r-eye',
               'bone_r_clavicle' : 'bone_r-clavicle',
               'bone_r_upperarmtwist1' : 'bone_r-upperarmtwist1',
               'bone_r_foretwist' : 'bone_r-foretwist',
               'bone_r_elbow' : 'bone_r-elbow',
               'bone_r_foretwist1' : 'bone_r-foretwist1',
               'bone_r_hand' : 'bone_r-hand',
               'bone_r_finger1' : 'bone_r-finger1',
               'bone_r_finger11' : 'bone_r-finger11',
               'bone_r_finger2' : 'bone_r-finger2',
               'bone_r_finger21' : 'bone_r-finger21',
               'bone_r_finger3' : 'bone_r-finger3',
               'bone_r_finger31' : 'bone_r-finger31',
               'bone_r_finger4' : 'bone_r-finger4',
               'bone_r_finger41' : 'bone_r-finger41',
               'bone_r_handprop' : 'bone_r-handprop',
               'bone_r_thumb1' : 'bone_r-thumb1',
               'bone_r_thumb11' : 'bone_r-thumb11',
               'bone_r_upperarmtwist2' : 'bone_r-upperarmtwist2',
               'bone_r_upperarmtwist3' : 'bone_r-upperarmtwist3' }

# Material String Dictionaries
MATERIAL_TAGS = { 'Diffuse_Map_varList' : 'diffuse_map',
                  'Diffuse_Map' : 'diffuse_map',
                  'Pattern_Map_varList' : 'diffuse_map',
                  'pattern_map' : 'diffuse_map',
                  'Normal_Map_varList' : 'normal_map',
                  'Normal_Map' : 'normal_map',
                  'Normal_Map_Height' : 'normal_map_height',
                  'material_name' : 'name',
                  'mtl_id' : 'index',
                  'Blend_Map_varList' : 'blend_map',
                  'Blend_Map' : 'blend_map',
                  'Fresnel_Alpha_Interface' : 'fresnel_alpha_interface',
                  'Fresnel_Alpha_Interface_2' : 'fresnel_alpha_interface2',
                  'Fresnel_Strength' : 'fresnel_strength',
                  'Fresnel_Strength_2' : 'fresnel_strength2',
                  'Specular_Map_varList' : 'specular_map',
                  'Specular_Map' : 'specular_map',
                  'Specular_Map_Amount' : 'specular_map_amount',
                  'Specular_Power' : 'specular_power',
                  'Specular_Power_2' : 'specular_power2',
                  'Specular_Alpha' : 'specular_alpha',
                  'Specular_Alpha_2' : 'specular_alpha2',
                  'Specular_Alpha_Interface' : 'specular_alpha_interface',
                  'Specular_Alpha_Interface_2' : 'specular_alpha_interface2',
                  'Sphere_Map_varList' : 'sphere_map1',
                  'Sphere_Map_Amount' : 'sphere_map_amount',
                  'Sphere_Map_1_varList' : 'sphere_map1',
                  'Sphere_Map_2_varList' : 'sphere_map2',
                  'Sphere_Map_2' : 'sphere_map2',
                  'Sphere_Map_1' : 'sphere_map1',
                  'Sphere_Map' : 'sphere_map1',
                  'Base_Opacity' : 'base_opacity',
                  'shader' : 'shader',
                  'Texture' : 'texture',
                  'Self_Illumination' : 'self_illumination',
                  'glow_Mask_Map' : 'glow_Mask_Map',
                  }


class Node_Bone( object ):
	"""
	Fbx bone object

	*Arguments:*
		* ``node`` Fbx node for the bone
		* ``scene`` Fbx scene

	*Keyword Arguments:*
		* ``none``

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   11/19/2013 9:27:47 PM
	"""

	def __init__( self, node, scene ):
		self.node       = node
		self.name       = node.GetName( )
		self.id         = None
		self.index      = None
		self.parent     = None
		self.parent_id  = None
		self.parent_index = None

		object_transform = compute_world_transform( node )
		self.quat = object_transform.GetQ( )
		self.pos  = object_transform.GetT( )

		#print '{4} Quat: {0} {1} {2} {3}'.format( self.quat[0], self.quat[1], self.quat[2], self.quat[3], self.name )

		self.update_attributes( )


	def update_attributes( self ):
		"""
		Update the attribute values on this bone

		*Arguments:*
			* ``None``

		*Keyword Arguments:*
			* ``None``

		*Returns:*
			* ``Value`` If any, enter a description for the return value here.

		*Examples:* ::

			Enter code examples here. (optional field)

		*Todo:*
			* Enter thing to do. (optional field)

		*Author:*
			* Randall Hess,  1/20/2014 12:50:07 PM
		"""
		#print 'IN: Bone index: {0} Bone id: {1} Parent: {2} Parent id: {3}'.format( self.index, self.id, self.parent, self.parent_id )

		# get the index of this bone
		bone_index = get_node_properties( self.node, property_name = 'p_bone_order',  get_value = True )
		if not bone_index is None:
			self.index = bone_index

		# get the bone id
		bone_id = get_node_properties( self.node, property_name = 'p_bone_id', get_value = True )
		if not bone_id is None:
			self.id = bone_id

		# get the parent index
		parent = get_node_properties( self.node, property_name = 'p_bone_parent', get_value = True )
		if not parent is None:
			self.parent = parent

		bone_name = get_node_properties( self.node, property_name = 'p_bone_name', get_value = True )
		if not bone_name is None:
			self.name = str( bone_name )
		else:
			self.name = get_bone_name( self.name )

		if self.name == 'bone_root':
			self.index = 0

		#print 'OUT: Bone index: {0} Bone id: {1} Parent: {2} Parent id: {3}'.format( self.index, self.id, self.parent, self.parent_id )


class Node_Tag( object ):
	"""
	Fbx tag object

	*Arguments:*
		* ``node`` Fbx node for the bone
		* ``scene`` Fbx scene

	*Keyword Arguments:*
		* ``none``

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   11/19/2013 9:27:47 PM
	"""

	def __init__( self, node, scene ):
		self.node    = node
		self.name    = node.GetName( )
		self.parent  = node.GetParent( )
		self.parent_index = 0

		# get the transform then remove the scale from the tags
		object_transform = compute_world_transform( node )
		object_transform = remove_transform_scale( object_transform )

		# get the rotation
		self.quat = object_transform.GetQ( )

		# get the position relative to the parent
		parentNode = node.GetParent()
		parent_object_transform = compute_world_transform( parentNode )
		self.pos  = object_transform.GetT( ) - parent_object_transform.GetT( )

		tag_name = get_node_properties( self.node, property_name = 'p_tag_name', get_value = True )
		if not tag_name is None:
			self.name = tag_name
		else:
			self.name = get_tag_name( self.name )



class Vertex_Info( object ):
	"""
	Store off all the data relative to a vertex

	*Arguments:*
		* ``Argument`` Enter a description for the argument here.

	*Keyword Arguments:*
		* ``Argument`` Enter a description for the keyword argument here.

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   12/23/2013 9:48:50 PM
	"""

	def __init__( self, vertex_index ):

		self.index = -1
		self.positions = [ 0, 0, 0, 0 ]
		self.normal = [ 0, 0, 0 ]
		self.uvs = [ 0, 0 ]
		self.original_index = -1



class Node_Info( object ):
	"""
	Structure to hold triangle/face data for a mesh

	*Arguments:*
	* ``node`` fbx object
		* ``node_index`` Index of the object in the scene heirarchy

	*Keyword Arguments:*
		* ``Argument`` Enter a description for the keyword argument here.

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   12/17/2013 8:58:16 PM
	"""

	def __init__( self, node, node_index ):

		self.index = node_index
		self.node = node
		self.parent = node.GetParent()


class Face_Info( object ):
	"""
	Structure to hold triangle/face data for a mesh

	*Arguments:*
		* ``face_index`` Index of the triangle/face in the mesh

	*Keyword Arguments:*
		* ``Argument`` Enter a description for the keyword argument here.

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   12/17/2013 8:58:16 PM
	"""

	def __init__( self, face_index ):

		self.index = face_index
		self.material_id = 0
		self.verts = [ 0, 0, 0 ]
		self.indices = [ 0, 0, 0 ]



class Material_Info( object ):
	"""
	Structure to hold default material data

	*Arguments:*
		* ``index`` Index of the material
		* ``name`` Name of the material

	*Keyword Arguments:*
		* ``None``

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   12/17/2013 8:58:16 PM
	"""

	def __init__( self, index, name ):

		self.index = index
		self.name = name
		self.diffuse_map = os.path.join( WORKING_DIR, 'missing.tga' )
		self.normal_map = os.path.join( WORKING_DIR, 'normal_blank_n.tga' ) #'flat-normalmap_n.tga'
		self.normal_map_height = 1.000000
		self.specular_map = os.path.join( WORKING_DIR, 'spec_blank_s.tga' )
		self.specular_map_amount = 1.000000
		self.specular_power = 60.000000
		self.specular_power2 = 60.000000
		self.specular_alpha = 0.000000
		self.specular_alpha2 = 0.000000
		self.specular_alpha_interface = 1.000000
		self.specular_alpha_interface2 = 0.000000
		self.sphere_map1 = os.path.join( WORKING_DIR, 'missing-grey.tga' )
		self.sphere_map2 = os.path.join( WORKING_DIR, 'missing-grey.tga' )
		self.sphere_map_amount = 1.000000
		self.pattern = os.path.join( WORKING_DIR, 'missing.tga' )
		self.dob = os.path.join( WORKING_DIR, 'missing.tga' )
		self.blend_map = os.path.join( WORKING_DIR, 'shd_whiteopaque.tga' )
		self.shader = os.path.join( WORKING_DIR, 'ir_bbsimple1' )
		self.base_opacity = 1.000000
		self.texture = os.path.join( WORKING_DIR, 'norender.tga' )
		self.fresnel_alpha_interface = 0.000000
		self.fresnel_alpha_interface2 = 0.000000
		self.fresnel_strength = 0.000000
		self.fresnel_strength2 = 0.000000
		self.self_illumination = 0.000000
		self.glow_Mask_Map = os.path.join( WORKING_DIR, 'missing.tga' )
		self.xml_element = None
		self.pattern_map = os.path.join( WORKING_DIR, 'missing-black.tga' )


def get_process( process_name ):

	ps_api = ctypes.WinDLL( 'Psapi.dll' )

	ps_api.EnumProcesses.restype = ctypes.wintypes.BOOL
	ps_api.GetProcessImageFileNameA.restype = ctypes.wintypes.DWORD

	kernel32 = ctypes.WinDLL( 'kernel32.dll' )

	kernel32.OpenProcess.restype = ctypes.wintypes.HANDLE
	kernel32.TerminateProcess.restype = ctypes.wintypes.BOOL

	MAX_PATH = 260
	PROCESS_TERMINATE = 0x0001
	PROCESS_QUERY_INFORMATION = 0x0400

	count = 32

	process_count = 0

	while True:
		process_ids = ( ctypes.wintypes.DWORD * count )( )
		cb = ctypes.sizeof( process_ids )
		bytes_returned = ctypes.wintypes.DWORD( )

		if ps_api.EnumProcesses( ctypes.byref( process_ids ), cb, ctypes.byref( bytes_returned ) ):
			if bytes_returned.value < cb:
				break

			else:
				count *= 2
		else:
			raise IOError( 'Call to EnumProcesses failed' )


	for index in range( bytes_returned.value / ctypes.sizeof( ctypes.wintypes.DWORD ) ):
		process_id = process_ids[ index ]
		h_process = kernel32.OpenProcess( PROCESS_QUERY_INFORMATION, False, process_id )
		if h_process:
			image_filename = ( ctypes.c_char*MAX_PATH )( )

			if ps_api.GetProcessImageFileNameA( h_process, image_filename, MAX_PATH ) > 0:
				filename = os.path.basename( image_filename.value ).lower( )

				if filename == process_name:
					process_count += 1

			kernel32.CloseHandle( h_process )

	return process_count


def package_files( converted_folder, output_folder ):
	"""
	Package the output files into str2_pc and asm_pc packages
	Command line call to vpckg

	*Arguments:*
		* ``file_folder`` Location of converted *_pc files
		* ``output_folder`` Location of destination *_asm_pc, *_str2_pc files

	*Keyword Arguments:*
		* ``Argument`` Enter a description for the keyword argument here.

	*Returns:*
		* ``Boolean`` Succeed

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess, randall.hess@volition-inc.com, 7/16/2014 4:03:47 PM
	"""

	package_executable = os.path.join( WORKING_DIR, 'vpkg_wd.exe' )
	if not os.path.lexists( package_executable ):
		wx.MessageBox( 'vpkg_wd.exe was missing from the converter director', style = wx.OK, caption = 'Volition FBX Converter' )
		return False

	print 'Getting converted files'
	#converted_files = [ ]
	#filenames = [ ]
	#for dirpath, dirnames, filenames in os.walk( converted_folder ):
		#converted_files.extend( filenames )
		#for filename in filenames:
			#if filename.endswith( '_pc' ):
				#print ' adding converted file: {0}'.format( filename )

	print 'Getting asm files'
	asm_files = [ ]
	filenames = [ ]
	for dirpath, dirnames, filenames in os.walk( output_folder ):
		for filename in filenames:
			if filename.endswith( 'asm_pc' ):
				asm_file = os.path.join( output_folder, filename )
				if not asm_file in asm_files:
					asm_files.append( asm_file )
					print ' adding asm file: {0}'.format( asm_file )

	print 'Getting str2 files'
	str2_files = [ ]
	filenames = [ ]
	for dirpath, dirnames, filenames in os.walk( output_folder ):
		for filename in filenames:
			if filename.endswith( 'str2_pc' ):
				str2_file = os.path.join( output_folder, filename )
				if not str2_file in str2_files:
					str2_files.append( str2_file )
					print ' adding str2 file: {0}'.format( str2_file )

	# Backup Original Str2 and Asm files
	backup_path = os.path.join( output_folder, 'backup' )
	if not os.path.lexists( backup_path ):
		os.mkdir( backup_path )

	if len( asm_files ) == 0:
		wx.MessageBox( 'You do no appear to have any unpacked asm/str2 files in the Package folder.\nPlease refer to the tutorial section for unpacking these files.', style = wx.OK, caption = 'Volition FBX Converter' )
		return False

	for asm_file in asm_files:
		try:
			shutil.copy2( asm_file, backup_path )
		except IOError:
			print 'FAILED to backup copy {0}'.format( asm_file )


	for str2_file in str2_files:
		try:
			shutil.copy2( str2_file, backup_path )
		except IOError:
			print 'FAILED to backup copy {0}'.format( str2_file )


	# loop through each str2_pc and sub asm_pc
	print 'Attempting to update SaintsRow asm/str2 files: {0}'.format( output_folder )
	output_cmds = [ ]
	command_failed = [ ]
	command_index = 0

	for str2_file in str2_files:
		for asm_file in asm_files:

			command_index += 1
			cmd = 'vpkg_wd -output_dir "{0}" -update_str2 "{1}" "{2}" "{3}\*"'.format( output_folder, str2_file, asm_file, converted_folder )
			output_cmds.append( cmd )
			print cmd

			try:
				subprocess.check_call( cmd, shell = False, stderr = subprocess.STDOUT)
			except subprocess.CalledProcessError as error:
				code = error.returncode
				command_failed.append( command_index )
				if code in ( 1, 2 ):
					print 'The command failed\n  {0}'.format( cmd )
				elif code in ( 3, 4, 5 ):
					print 'The command had some issues\n  {0}'.format( cmd )

			finally:
				processed = True

			time.sleep( 0.25 )

	# print out the commands that were run
	for index in range( 0, len( output_cmds ) ):
		if not index in command_failed:
			print '{0}'.format( output_cmds[ index ] )
		else:
			print 'FAILED: {0}'.format( output_cmds[ index ] )

	return True

	return False


def crunch_rule( filename, ):
	"""
	Call the specific cruncher based on the prefix of the given filename

	*Arguments:*
		* ``filename`` .rule filename

	*Keyword Arguments:*
		* ``none``

	*Returns:*
		* ``Bool`` If the file crunched

	*Examples:* ::

		crunch_rule( mesh_crunch_wd_pc_Clip.rule )
		  mesh_crunch_wd.exe -p shaders.vpp_pc "mesh_crunch_wd_pc_Clip.rule"


	*Author:*
		* Randall Hess, 4/24/2014 10:21:02 PM
	"""

	if os.path.lexists( filename ):

		# check for the shaders.vpp_pc
		shaders_file = os.path.join( WORKING_DIR, 'shaders.vpp_pc' )
		if os.path.lexists( shaders_file ):

			# Get the cruncher from the startswith rule filename
			for cruncher in CRUNCHERS:
				base_filename = os.path.basename( filename )
				if base_filename.startswith( cruncher ):
					cruncher_file = os.path.join( WORKING_DIR, (cruncher + '.exe') )
					if os.path.lexists( cruncher_file ):
						# copy the cruncher file to the rule file location
						#try:
							#shutil.copy2( cruncher_file, os.path.dirname( filename ) )
						#except IOError:
							#pass

						#copied_cruncher_file = os.path.join( os.path.dirname( filename ), '{0}.exe'.format( cruncher ) )

						copied_cruncher_file = cruncher_file
						if os.path.lexists( cruncher_file ):
							if base_filename.startswith( MESH_CRUNCHER ) or base_filename.startswith( MAT_CRUNCHER ):
								print '{0} -p {1} {2}'.format( copied_cruncher_file, shaders_file, filename )
								subprocess.Popen( '"{0}" -p "{1}" "{2}"'.format( copied_cruncher_file, shaders_file, filename ) )
							else:
								subprocess.Popen( '"{0}" "{1}"'.format( copied_cruncher_file, filename ) )

							# remove the file
							#os.remove( copied_cruncher_file )
							return True

						else:
							print 'ERROR: Cannot crunch. Cruncher file does not exist.\n{0}'.format( cruncher_file )
					else:
						print 'ERROR: Cannot crunch. Cruncher file does not exist.\n{0}'.format( cruncher_file )
		else:
			print 'ERROR: Cannot crunch. Shaders file does not exist.\n{0}'.format( shaders_file )
	else:
		print 'ERROR: Cannot crunch. Rule file does not exist.\n{0}'.format( filename )

	return False


def pretty_xml( element ):
	"""
	Format xml to pretty xml

	*Arguments:*
		* ``element`` Top level xml element to prettify

	*Keyword Arguments:*
		* ``None``

	*Returns:*
		* ``string`` Prettyfied xml string

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   12/27/2013 2:30:46 PM
	"""

	temp_string = xml.etree.cElementTree.tostring( element ) # 'utf-8' )
	parse_string = xml.dom.minidom.parseString( temp_string )
	return parse_string.toprettyxml( indent = '\t' )


def get_shaders_from_xml( xml_file ):
	"""
	Get a list of shaders from the given xml file ( sr_shaders.xml )

	*Arguments:*
		* ``xml_file`` Shader xml file

	*Returns:*
		* ``list`` list of shader names

	*Author:*
		* Randall Hess, , 1/2/2014 5:42:31 PM
	"""

	if not os.path.lexists( xml_file ):
		wx.MessageBox( 'Xml Shaders file is missing!\n' + xml_file, style = wx.OK, caption = 'Volition FBX Converter' )
		return [ ], { }

	shader_names = [ ]
	material_elements = { }
	try:
		xml_doc = xml.etree.cElementTree.parse( xml_file )
	except:
		wx.MessageBox( 'Could not parse ' + xml_file, style = wx.OK, caption = 'Volition FBX Converter' )
		return shader_names, { }

	xml_root = xml_doc.getroot( )
	table = xml_root.find( 'materials' )
	materials = table.findall( 'material' )
	for material in materials:
		name = material.find( 'shader' )
		shader_names.append( name.text )
		material_elements[ name.text ] = material

	shader_names.sort( )
	return shader_names, material_elements


def write_crunch_rule( filename, resource_type, textures = None ):
	"""
	Write the rule to send to the cruncher

	*Arguments:*
		* ``filename`` List of source filename of the rule to create
		* ``resource_type`` The type of resource to create a rule for

	*Keyword Arguments:*
		* ``None``

	*Returns:*
		* ``Value`` If any, enter a description for the return value here.

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   12/26/2013 3:16:36 PM
	"""

	resources = { '.matlibx' : 'material_library',
		           '.cmeshx' : 'character_mesh',
		           '.rigx' : 'rig',
		           '.peg' : 'texture_target',
		           '.texture' : 'texture',
		           '.smeshx' : 'static_mesh',
	              '.morphx' : 'morph' }

	crunch_targets = { '.matlibx' : [ '.matlib_' ],
		                '.cmeshx' : [ '.ccmesh_', '.gcmesh_', '.morph_key_' ],
		                '.rigx' : [ '.rig_' ],
		                '.peg' : [ '.cpeg_', '.gpeg_' ],
		                '.texture' : [ '.cvbm_', '.gvbm_', '.acl_' ],
		                '.smeshx' : [ '.csmesh_', '.gsmesh_' ],
	                   '.morphx' : [ '.cmorph_', '.gmorph_' ] }

	crunch_names = { '.rigx' : 'rig_cruncher_wd_',
		              '.cmeshx' : 'mesh_crunch_wd_',
		              '.peg' : 'peg_assemble_wd_',
		              '.matlibx' : 'material_library_crunch_wd_',
		              '.texture' : 'texture_crunch_wd_',
		              '.smeshx' : 'mesh_crunch_wd_',
	                 '.morphx' : 'morph_crunch_wd_' }

	source_types = { '.peg' : [ '.cvbm_', '.gvbm_' ] }

	# write rule header
	platform = 'pc'
	header = xml.etree.cElementTree.Element( 'ctg' )
	in_platforms = xml.etree.cElementTree.SubElement( header, 'in_platforms' )
	cur_platform = xml.etree.cElementTree.SubElement( in_platforms, 'platform' )
	cur_platform.text = platform
	base_name = None
	base_no_ext = None

	# make the outuput folder
	crunch_path = os.path.join( os.path.dirname( filename ), 'output' )
	if not os.path.lexists( crunch_path ):
		os.mkdir( crunch_path )

	if not resource_type == '.peg':

		# write the source filename
		source = xml.etree.cElementTree.SubElement( cur_platform, 'source' )
		if resource_type == '.texture':
			base_name = os.path.basename( textures )
			source.text = os.path.join( os.path.dirname( filename ), base_name )

		elif resource_type == '.morphx':
			morph_key_name = os.path.basename( filename ).replace( '_pc.morphx', '.morph_key_pc' )
			source.text = os.path.join( crunch_path, morph_key_name )
			source1 = xml.etree.cElementTree.SubElement( cur_platform, 'source' )
			base_name = os.path.basename( filename )
			source1.text = filename

		else:
			base_name = os.path.basename( filename )
			source.text = filename
		base_no_ext = os.path.splitext( base_name )[ 0 ]

	else:
		# write texture source files into the peg rule
		data_types = source_types[ resource_type ]
		for texture in textures:
			for data in data_types:
				base_name = os.path.basename( texture )
				base_no_ext = os.path.splitext( base_name )[ 0 ]
				base_data_ext = base_no_ext + data + platform
				source = xml.etree.cElementTree.SubElement( cur_platform, 'source' )
				source.text = os.path.join( os.path.dirname( filename ), base_data_ext )
				## TO-DO handle additional attrs.. ( texture_is_linear_color_space, normal_map )

	# output target files
	targets = crunch_targets[ resource_type ]
	for target in targets:
		temp_target = xml.etree.cElementTree.SubElement( cur_platform, 'target' )
		if resource_type == '.peg':
			base_name = os.path.basename( filename )
			base_no_ext = os.path.splitext( base_name )[ 0 ]
			target_filename = base_no_ext + target + platform
			temp_target.text = os.path.join( crunch_path, target_filename )
		else:
			target_filename =  base_no_ext + target + platform
			if resource_type == '.texture':
				temp_target.text = os.path.join( os.path.dirname( filename ), target_filename )
			else:
				temp_target.text = os.path.join( crunch_path, target_filename )

	# make the log folder
	log_path = os.path.join( os.path.dirname( filename ), 'logs' )
	if not os.path.lexists( log_path ):
		os.mkdir( log_path )

	# handle texture or peg logs
	if resource_type == '.texture' or resource_type == '.peg':
		log = xml.etree.cElementTree.SubElement( header, 'log' )

		log.text = os.path.join( log_path, ( 'log_' + base_no_ext + '_' + resources[ resource_type ] + '.txt' ) )
		warnings_as_errors = xml.etree.cElementTree.SubElement( header, 'warnings_as_errors' )
		warnings_as_errors.text = 'true'
		errors_are_fatal = xml.etree.cElementTree.SubElement( header, 'errors_are_fatal' )
		errors_are_fatal.text = 'true'
	# handle other logs
	else:
		log = xml.etree.cElementTree.SubElement( header, 'log' )
		log.text = os.path.join( log_path, 'log2_' + base_no_ext + '_' + resources[ resource_type ] +  '.txt' )
		warnings_as_errors = xml.etree.cElementTree.SubElement( header, 'warnings_as_errors' )
		warnings_as_errors.text = 'true'
		errors_are_fatal = xml.etree.cElementTree.SubElement( header, 'errors_are_fatal' )
		errors_are_fatal.text = 'true'

	# write out the mesh crunch rule file
	rule_xml = pretty_xml( header )
	crunch_name = crunch_names[ resource_type ] + platform + '_' + base_no_ext + '.rule'
	crunch_file =  os.path.join( log_path, crunch_name )
	with open( crunch_file, 'w' ) as crunch_rule:
		crunch_rule.write( rule_xml )

	return crunch_file


def write_matlibx( filename, materials ):
	"""
	Write the material library xml file

	*Arguments:*
		* ``filename`` the *.cmeshx filepath and name
		* ``materials`` list of materials

	*Keyword Arguments:*
		* ``none``

	*Returns:*
		* ``bool`` bool if the file has successfully been written

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   11/19/2013 8:46:57 PM
	"""

	with open( filename, 'w' ) as matlibx_file:

		# write header
		matlibx_file.write( '<root>\n' )
		matlibx_file.write( '\t<header>\n' )
		matlibx_file.write( '\t\t<signature>RFMT</signature>\n' )
		matlibx_file.write( '\t\t<version>1</version>\n' )
		matlibx_file.write( '\t</header>\n' )

		matlibx_file.write( '\t\t<material_library>\n' )

		for material in materials:
			matlibx_file.write( '\t\t\t<material>\n' )
			write_material( matlibx_file, material, tabs = '\t\t\t\t' )
			matlibx_file.write( '\t\t\t</material>\n' )

		matlibx_file.write( '\t\t</material_library>\n' )
		matlibx_file.write( '</root>\n' )

		return True

	return False


def write_morphx( filename, cmeshx_filename, mesh, mesh_name, vertices, blendshapes, face_data, ordered_verts ):
	"""
	Write the morphx xml file

	*Arguments:*
		* ``filename`` the *.cmeshx filepath and name
		* ``mesh`` the fbx mesh node
		* ``mesh_name`` name of the mesh
		* ``face_data`` data identifying all of the triangles, verts, uvs and normals
		* ``vertices`` list of vertices
		* ``bone_order`` dictionary of fbx_nodes and the index of the bone
		* ``tags`` list of tags or prop points on the mesh
		* ``materials`` list of materials
		* ``bone_weights`` list of bones, verts and their associated weight values

	*Keyword Arguments:*
		* ``none``

	*Returns:*
		* ``bool`` bool if the file has successfully been written

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   11/19/2013 8:46:57 PM
	"""

	with open( filename, 'w' ) as morphx_file:

		debug_output = False

		# write header
		morphx_file.write( '<root>\n' )
		morphx_file.write( '\t<morph_version>65537</morph_version>\n' )
		morphx_file.write( '\t<vcm_filename>{0}</vcm_filename>\n'.format( os.path.basename( cmeshx_filename ) ) )
		morphx_file.write( '\t<compress>true</compress>\n' )


		# write targets
		morphx_file.write( '\t<targets>\n' )
		for blend_name, blend_values in blendshapes.iteritems( ):

			# target name, num > verts
			morphx_file.write( '\t\t<target>\n' )
			morphx_file.write( '\t\t\t<name>{0}</name>\n'.format( blend_name ) )
			morphx_file.write( '\t\t\t<num_verts>{0}</num_verts>\n'.format( len( blend_values ) ) )
			morphx_file.write( '\t\t\t<verts>\n' )

			for vert_data in ordered_verts:
				# vert index, pos, normal
				for blendvert_index, blendvert_values in sorted( blend_values.iteritems( ) ):
					if blendvert_index == vert_data.original_index:
						morphx_file.write( '\t\t\t\t<vert>\n' )
						vert = blendvert_values[0]
						norm = blendvert_values[1]

						## convert the vertex floats into hex
						#vert_x = get_float_as_hex( -vert[ 0 ] )
						#vert_y = get_float_as_hex( vert[ 2 ] )
						#vert_z = get_float_as_hex( -vert[ 1 ] )

						if DEBUG_OUTPUT:
							morphx_file.write( '\t\t\t\t\t{0}         {1}        {2}\n'.format( round( -vert_data.positions[0], 5 ),  round( vert_data.positions[2], 5 ), round( -vert_data.positions[1], 5 ) ) )
							morphx_file.write( '\t\t\t\t\toriginal index: {0}\n'.format( vert_data.original_index ) )

						morphx_file.write( '\t\t\t\t\t<orig_index>{0}</orig_index>\n'.format( vert_data.index ) )
						morphx_file.write( '\t\t\t\t\t<delta_pos>{0:.5f} {1:.5f} {2:.5f}</delta_pos>\n'.format( -vert[0], vert[2], -vert[1] ) )
						morphx_file.write( '\t\t\t\t\t<delta_norms>{0:.5f} {1:.5f} {2:.5f}</delta_norms>\n'.format( -norm[0], norm[2], -norm[1] ) )
						morphx_file.write( '\t\t\t\t</vert>\n' )

			morphx_file.write( '\t\t\t</verts>\n' )
			morphx_file.write( '\t\t</target>\n' )

		morphx_file.write( '\t</targets>\n' )
		morphx_file.write( '</root>\n' )

		return True

	return False


def write_cmeshx( filename, mesh, mesh_name, face_data, vertices, bone_order, tags, materials, bone_weights, static_mesh = True ):
	"""
	Write the cmeshx xml file

	*Arguments:*
		* ``filename`` the *.cmeshx filepath and name
		* ``mesh`` the fbx mesh node
		* ``mesh_name`` name of the mesh
		* ``face_data`` data identifying all of the triangles, verts, uvs and normals
		* ``vertices`` list of vertices
		* ``bone_order`` dictionary of fbx_nodes and the index of the bone
		* ``tags`` list of tags or prop points on the mesh
		* ``materials`` list of materials
		* ``bone_weights`` list of bones, verts and their associated weight values

	*Keyword Arguments:*
		* ``none``

	*Returns:*
		* ``bool`` bool if the file has successfully been written

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   11/19/2013 8:46:57 PM
	"""

	with open( filename, 'w' ) as cmeshx_file:

		debug_output = False

		# write header
		cmeshx_file.write( '<root>\n' )
		cmeshx_file.write( '\t<header>\n' )
		cmeshx_file.write( '\t\t<signature>RFCM</signature>\n' )
		cmeshx_file.write( '\t\t<version>1</version>\n' )
		if not static_mesh:
			cmeshx_file.write( '\t\t<rig_version>1</rig_version>\n' )
		cmeshx_file.write( '\t</header>\n' )

		# write bones
		if not static_mesh:
			bones = { }
			index = 0
			cmeshx_file.write( '\t<bones>\n' )
			for bone_index in sorted( bone_order ):
				bone = bone_order[ bone_index ]
				bones[ bone.name ] = index
				cmeshx_file.write( '\t\t<bone>\n' )
				cmeshx_file.write( '\t\t\t<name>bone-{0}</name>\n'.format( bone.name ) ) #get_bone_name( bone.name ) ) )
				cmeshx_file.write( '\t\t\t<index>{0}</index>\n'.format( index ) )
				cmeshx_file.write( '\t\t\t<id>{0}</id>\n'.format( bone.id ) )
				cmeshx_file.write( '\t\t\t<transform>\n' )
				cmeshx_file.write( '\t\t\t\t{0:.6f} {1:.6f} {2:.6f}\n'.format( -bone.pos[0], -bone.pos[1], bone.pos[2] ) )
				cmeshx_file.write( '\t\t\t\t{0:.6f} {1:.6f} {2:.6f} {3:.6f}\n'.format( bone.quat[0], bone.quat[1], bone.quat[2], bone.quat[3] ) )
				cmeshx_file.write( '\t\t\t</transform>\n' )
				cmeshx_file.write( '\t\t\t<parentbone>{0}</parentbone>\n'.format( bone.parent ) )
				cmeshx_file.write( '\t\t\t<parent_id>{0}</parent_id>\n'.format( bone.parent_id ) )
				cmeshx_file.write( '\t\t\t<flags>{0}</flags>\n'.format( '' ) )
				cmeshx_file.write( '\t\t</bone>\n' )
				index += 1
			cmeshx_file.write( '\t</bones>\n' )

			# write tags
			cmeshx_file.write( '\t<tags>\n' )
			for tag in tags:
				cmeshx_file.write( '\t\t<tag>\n' )
				cmeshx_file.write( '\t\t\t<name>$prop-{0}</name>\n'.format( tag.name ) ) #get_tag_name( tag.name ) ) )
				cmeshx_file.write( '\t\t\t<parentbone>{0}</parentbone>\n'.format( tag.parent_index ) )
				cmeshx_file.write( '\t\t\t<transform>\n' )
				cmeshx_file.write( '\t\t\t\t{0:.6f} {1:.6f} {2:.6f}\n'.format( -tag.pos[0], -tag.pos[1], tag.pos[2] ) )
				cmeshx_file.write( '\t\t\t\t{0:.6f} {1:.6f} {2:.6f} {3:.6f}\n'.format( tag.quat[0], tag.quat[1], tag.quat[2], tag.quat[3] ) )
				cmeshx_file.write( '\t\t\t</transform>\n' )
				cmeshx_file.write( '\t\t</tag>\n' )
			cmeshx_file.write( '\t</tags>\n' )

			# rig indices
			cmeshx_file.write( '\t<rigindices>\n' )
			index = 0
			for bone_index in bone_order:
				cmeshx_file.write( '\t\t<index>{0}</index>\n'.format( index ) )
				index +=1
			cmeshx_file.write( '\t</rigindices>\n' )

			#TODO - Get spheres or cylinders linked to bones
			# collision primitive
			cmeshx_file.write( '\t<collision_prims>\n' )
			cmeshx_file.write( '\t</collision_prims>\n' )

		# Mesh Block
		cmeshx_file.write( '\t\t<mesh>\n' )
		cmeshx_file.write( '\t\t\t<name>{0}</name>\n'.format( mesh_name ) )
		cmeshx_file.write( '\t\t\t<parentname>{0}</parentname>\n'.format( 'none' ) )
		cmeshx_file.write( '\t\t\t<numverts>{0}</numverts>\n'.format( len( vertices ) ) )
		cmeshx_file.write( '\t\t\t<numfaces>{0}</numfaces>\n'.format( len( face_data ) ) )

		# Materials
		cmeshx_file.write( '\t\t\t<materials>\n' )

		# TODO - Determine how to write out all of the material block info we need
		for material in materials:
			cmeshx_file.write( '\t\t\t\t<material>\n' )
			write_material( cmeshx_file, material )
			cmeshx_file.write( '\t\t\t\t</material>\n' )

		cmeshx_file.write( '\t\t\t</materials>\n' )


		# **************************************************************
		# Verts
		cmeshx_file.write( '\t\t\t<verts>\n' )
		cmeshx_file.write( '\t\t\t\t<hex>1</hex>\n' )


		# write the verts
		vert_index = 0
		vert_indices = [ ]
		ordered_verts = [ ]
		for face in face_data:
			vert_idx = 0
			for vert_data in face.verts:
				# make sure we haven't already written this vertex index
				if not vert_data.index in vert_indices:
					face.indices[ vert_idx ] = vert_index
					vert_indices.append( vert_data.index )
					vert = vert_data.positions

					# update the indicie for the morph targets
					ordered_vert_data = copy.deepcopy( vert_data )
					ordered_vert_data.index = vert_index
					ordered_vert_data.original_index = vert_data.index
					ordered_verts.append( ordered_vert_data )

					if DEBUG_OUTPUT:
						cmeshx_file.write( '\t\t\t\tIndex: {0} Vert: {1}\n'.format( vert_index, vert_data.index ) )
						cmeshx_file.write( '\t\t\t\t{0}         {1}        {2}\n'.format( round( -vert[0], 5 ),  round( vert[2], 5 ), round( -vert[1], 5 ) ) )

					# convert the vertex floats into hex
					vert_x = get_float_as_hex( -vert[ 0 ] )
					vert_y = get_float_as_hex( vert[ 2 ] )
					vert_z = get_float_as_hex( -vert[ 1 ] )

					# write out the converted vertex
					cmeshx_file.write( '\t\t\t\t<v>{0} {1} {2}</v>\n'.format( vert_x, vert_y, vert_z ) )

					vert_index += 1

				else:
					face.indices[ vert_idx ] = vert_indices.index( vert_data.index )

				vert_idx += 1

			if DEBUG_OUTPUT:
				print '\tFace: {0} Indices: {1}'.format( face.index, face.indices )

		cmeshx_file.write( '\t\t\t</verts>\n' )


		# **************************************************************
		# Normals
		cmeshx_file.write( '\t\t\t<normals>\n' )
		cmeshx_file.write( '\t\t\t\t<hex>1</hex>\n' )

		# write the normals
		vert_indices = [ ]
		for face in face_data:
			for vert_data in face.verts:
				# make sure we haven't already written this vertex index
				if not vert_data.index in vert_indices:
					vert_indices.append( vert_data.index )
					normal = vert_data.normal

					if DEBUG_OUTPUT:
						cmeshx_file.write( '\t\t\t\t{0}         {1}        {2}\n'.format( round( -normal[0], 5 ),  round( normal[2] , 5 ), round( -normal[1], 5 ) ) )

					# convert the values into hex
					normal_x = get_float_as_hex( -normal[ 0 ] )
					normal_y = get_float_as_hex( normal[ 2 ] )
					normal_z = get_float_as_hex( -normal[ 1 ] )

					# write out the converted vertex
					cmeshx_file.write( '\t\t\t\t<n>{0} {1} {2}</n>\n'.format( normal_x, normal_y, normal_z ) )
		cmeshx_file.write( '\t\t\t</normals>\n' )


		# **************************************************************
		# Faces
		cmeshx_file.write( '\t\t\t<faces>\n' )
		for face in face_data:
			cmeshx_file.write( '\t\t\t\t<f>{0} {1} {2} {3}</f>\n'.format( face.indices[0], face.indices[2], face.indices[1], face.material_id ) )
			#cmeshx_file.write( '\t\t\t\t<f>{0} {1} {2} {3}</f>\n'.format( face.indices[1], face.indices[0], face.indices[2], face.material_id ) )
		cmeshx_file.write( '\t\t\t</faces>\n' )


		# **************************************************************
		# FaceUvs
		cmeshx_file.write( '\t\t\t<faceuvs>\n' )
		cmeshx_file.write( '\t\t\t<hex>1</hex>\n' )

		for face in face_data:

			# build up the uv list for the current face, u and v for each face vertex
			corner_index = 0
			corner_uvs = [ 0, 0, 0, 0, 0, 0 ]
			corner_floats = [ 0, 0, 0, 0, 0, 0 ]

			for vert_data in face.verts:
				uv = vert_data.uvs

				if DEBUG_OUTPUT:
					print 'face index: {0}, vert: {1} uvs: {2}'.format( face.index, vert_data.index, uv )

				# store off the float values to print if debugging
				corner_floats[ corner_index ] = round( uv[0], 5 )
				corner_floats[ corner_index + 1 ] = round( uv[1], 5 )

				# convert uv values to hex
				uv_x = get_float_as_hex( uv[ 0 ] )
				uv_y = get_float_as_hex( uv[ 1 ] )

				# update the corner uv list with the proper indices
				corner_uvs[ corner_index ] = uv_x
				corner_uvs[ corner_index + 1 ] = uv_y
				corner_index += 2

			if DEBUG_OUTPUT:
				cmeshx_file.write( '\t\t\t\t{0}\t\t{1}\n'.format( round( corner_floats[0], 5 ), round(  corner_floats[1], 5 ) ) )
				cmeshx_file.write( '\t\t\t\t{0}\t\t{1}\n'.format( round( corner_floats[4], 5 ), round(  corner_floats[5], 5 ) ) )
				cmeshx_file.write( '\t\t\t\t{0}\t\t{1}\n'.format( round( corner_floats[2], 5 ), round(  corner_floats[3], 5 ) ) )

			cmeshx_file.write( '\t\t\t\t<uv>{0} {1} {2} {3} {4} {5}</uv>\n'.format( corner_uvs[0], corner_uvs[1], corner_uvs[4], corner_uvs[5], corner_uvs[2], corner_uvs[3], face.index ) )
		cmeshx_file.write( '\t\t\t</faceuvs>\n' )

		if not static_mesh:
			# **************************************************************
			# Vertex Weights
			cmeshx_file.write( '\t\t\t<vertexweights>\n' )
			cmeshx_file.write( '\t\t\t\t<numvweights>{0}</numvweights>\n'.format( len( vertices ) ) )
			cmeshx_file.write( '\t\t\t\t<vweights>\n' )


			# **************************************************************
			# Bone Weights

			# get the vert/weight info
			vert_indices = [ ]
			for face in face_data:
				vert_idx = 0
				for vert_data in face.verts:
					# make sure we haven't already written this vertex index
					if not vert_data.index in vert_indices:

						#face.indices[ vert_idx ] = vert_index
						vert_indices.append( vert_data.index )

						weight_info = bone_weights[ vert_data.index ]
						if weight_info:

							if DEBUG_VERTS:
								print 'Bone Weight: {2} VertIndex:{0} OriginalIndex:{1}'.format( vert_data.index, vert_data.original_index, weight_info )

							# vertex weights have a max of 4 bones per vert
							# values are paired - 0-255 to bone index
							weight_values = [ 0, -1, 0, -1, 0, -1, 0, -1 ]

							index = 0
							for bone, weight in weight_info.iteritems( ):
								# get the bone_index
								bone_index = bones[ bone ]

								# get the weight value converted to a byte value
								weight_byte = int( weight * 255.0 + 0.5 )

								# replace the current index in the weight values list
								weight_values[ index ] = weight_byte
								weight_values[ index + 1 ] = bone_index

								index += 2

							cmeshx_file.write( '\t\t\t\t\t<weight>{0:d} {1:d} {2:d} {3:d} {4:d} {5:d} {6:d} {7:d}</weight>\n'.format( weight_values[0], weight_values[1], weight_values[2], weight_values[3], weight_values[4], weight_values[5], weight_values[6], weight_values[7] ) )

				vert_idx += 1

			cmeshx_file.write( '\t\t\t\t</vweights>\n' )
			cmeshx_file.write( '\t\t\t</vertexweights>\n' )

		# Close Mesh Block
		cmeshx_file.write( '\t\t</mesh>\n' )

		if not static_mesh:
			# Auto Generate LODs
			cmeshx_file.write( '\t<AutoGenerateLODs>true</AutoGenerateLODs>\n' )

			# TODO - See if we actually use this
			# LOD flags
			cmeshx_file.write( '\t<LODParameterOverrides>\n' )
			cmeshx_file.write( '\t</LODParameterOverrides>\n' )

		# close the xml
		cmeshx_file.write( '</root>' )

		return True, ordered_verts

	# writing file failed
	return False, ordered_verts


def get_bone_name( name ):
	"""
	Get a proper bone name by removing a known prefix

	*Arguments:*
		* ``name`` object name

	*Keyword Arguments:*
		* ``none``

	*Returns:*
		* ``string`` string of the actual bone name

	*Author:*
		* Randall Hess, randall.hess@volition-inc.com, 4/28/2014 10:02:07 PM
	"""

	# fix a name with "-" in it
	bone_name = name.lower( )
	if "-" in bone_name:
		bone_name = bone_name.split( '-' )[1]
	elif 'bone_root' in bone_name:
		bone_name = 'bone_root'
	elif bone_name.startswith( 'bone_' ):
		if not 'bone_bone_' in bone_name:
			bone_name = bone_name.split( 'bone_')[1]
		else:
			bone_name = bone_name[5:]

	return bone_name


def get_tag_name( name ):
	"""
	Get a proper tag name by removing a known prefix

	*Arguments:*
		* ``name`` object name

	*Keyword Arguments:*
		* ``none``

	*Returns:*
		* ``string`` string of the actual tag name

	*Author:*
		* Randall Hess, randall.hess@volition-inc.com, 4/28/2014 10:02:07 PM
	"""

	# fix a name with "$prop-" in it
	tag_name = name.lower( )
	if tag_name.startswith( '$prop-' ):
		tag_name = tag_name.split( '$prop-' )[1]
	if tag_name.startswith( 'tag_' ):
		tag_name = tag_name.split( 'tag_')[1]

	return tag_name


def write_rigx( filename, bone_order, tags ):
	"""
	Write the rigx xml file

	*Arguments:*
		* ``filename`` the *.rigx filepath and name
		* ``bone_order`` dictionary of fbx_nodes and the index of the bone

	*Keyword Arguments:*
		* ``none``

	*Returns:*
		* ``bool`` bool if the file has been successfully written

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   11/19/2013 8:46:57 PM
	"""

	with open( filename, 'w' ) as rig_file:

		# write header
		rig_file.write( '<rig>\n' )
		rig_file.write( '\t<version>1</version>\n' )

		# write bones
		rig_file.write( '\t<bones>\n' )
		index = 0
		for index in sorted( bone_order ):
			bone = bone_order[ index ]
			rig_file.write( '\t\t<bone>\n' )
			rig_file.write( '\t\t\t<name>bone-{0}</name>\n'.format( bone.name ) ) #get_bone_name( bone.name ) ) )
			rig_file.write( '\t\t\t<index>{0}</index>\n'.format( index ) )
			rig_file.write( '\t\t\t<id>{0}</id>\n'.format( bone.id ) )
			rig_file.write( '\t\t\t<quat>{0:.6f} {1:.6f} {2:.6f} {3:.6f}</quat>\n'.format( bone.quat[0], bone.quat[1], -bone.quat[2], bone.quat[3] ) )
			rig_file.write( '\t\t\t<pos>{0:.6f} {1:.6f} {2:.6f}</pos>\n'.format( -bone.pos[0], -bone.pos[1], bone.pos[2] ) )
			rig_file.write( '\t\t\t<parent>{0}</parent>\n'.format( bone.parent ) )
			rig_file.write( '\t\t\t<parent_id>{0}</parent_id>\n'.format( bone.parent_id ) )
			rig_file.write( '\t\t</bone>\n' )
			index += 1
		rig_file.write( '\t</bones>\n' )

		# write tags
		rig_file.write( '\t<tags>\n' )
		for tag in tags:
			rig_file.write( '\t\t<tag>\n' )
			rig_file.write( '\t\t\t<name>$prop-{0}</name>\n'.format( tag.name ) ) #get_tag_name( tag.name ) ) )
			rig_file.write( '\t\t\t<parent>{0}</parent>\n'.format( tag.parent_index ) )
			rig_file.write( '\t\t\t<quat>{0:.6f} {1:.6f} {2:.6f} {3:.6f}</quat>\n'.format( tag.quat[0], -tag.quat[1], tag.quat[2], tag.quat[3] ) )
			rig_file.write( '\t\t\t<pos>{0:.6f} {1:.6f} {2:.6f}</pos>\n'.format( tag.pos[0], tag.pos[1], -tag.pos[2] ) )
			rig_file.write( '\t\t</tag>\n' )
		rig_file.write( '\t</tags>\n' )

		# close the xml
		rig_file.write( '</rig>' )

		return True

	# writing file failed
	return False


def get_large_texture( small_texture ):
	"""
	Get the large version of this texture if it exists.
	Return the file reference containing "_lg_" in place of "_sm_"

	*Arguments:*
		* ``small_texture`` texture file name containing '_sm_'

	*Keyword Arguments:*
		* ``none``

	*Returns:*
		* ``large_texture`` texture filename

	*Author:*
		* Randall Hess, randall.hess@volition-inc.com, 4/28/2014 9:59:12 PM
	"""

	# to try get lg versions of the textures
	if '_sm_' in small_texture.lower( ):

		# pass through lg textures if found
		for small, large in SMALL_LARGE_TEXTURES.iteritems( ):
			if small == small_texture:
				return large

	return None

def write_material( file_, material, tabs = '\t\t\t\t\t' ):
	"""
	Write the specific material into the file object

	*Arguments:*
		* ``file_`` file object we will write material info into
		* ``material`` the current fbx material object

	*Keyword Arguments:*
		* ``none``

	*Returns:*
		* ``Value`` If any, enter a description for the return value here.

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Create a material xml block for each SR3/4 character mesh shader

	*Author:*
		* Randall Hess,   11/19/2013 9:59:59 PM
	"""

	if material.xml_element:
		for element in material.xml_element.getchildren( ):
			element_value = element.text
			if element.text is None:
				# get the value from the material tags and material attributes
				if hasattr( material, MATERIAL_TAGS[ element.tag ] ):
					material_attr = getattr( material, MATERIAL_TAGS[ element.tag ] )
					element_value = material_attr

					# try to get the large texture
					if file_.name.endswith( '_high.matlibx' ):
						if isinstance( element_value, basestring ):
							large_texture = get_large_texture( element_value )
							if large_texture:
								element_value = large_texture

					if DEBUG_OUTPUT or DEBUG_MATERIAL:
						print 'Material Element: {0}, Material Value: {1}'.format( element.tag, element_value )
				else:
					element_value = ''

			if isinstance( element_value, basestring ):
				if element_value.endswith( '.tga' ):
					if os.path.dirname( element_value ):
						element_value = os.path.basename( element_value )
			file_.write( '{0}<{1}>{2}</{1}>\n'.format( tabs, element.tag, element_value ) )
	else:
		wx.MessageBox( ' Material is missing an assigned shader!\nMaterial: ' + material.name , style = wx.OK, caption = 'Volition FBX Converter' )
		return False

	return True


def get_scaled_value( value, scale, round_val = 5 ):
	"""
	Scale a floating point value

	*Arguments:*
		* ``value`` float value to scale
		* ``scale`` scale to apply

	*Keyword Arguments:*
		* ``round_val`` number of floating points to round up to

	*Returns:*
		* ``scaled_value`` updated scaled value

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   12/20/2013 6:05:00 PM
	"""

	return round( ( value / scale ), round_val )


def get_float_as_hex( value ):
	"""
	Do a conversion of the vertice float value
	From 3dsmax we will be converting from inches to meters.
	value / 39.3701
	Next we convert the float to a hex value

	*Arguments:*
		* ``vert_float`` float value of the

	*Keyword Arguments:*
		* ``none``

	*Returns:*
		* ``Value`` If any, enter a description for the return value here.

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   12/6/2013 1:46:17 PM
	"""

	hex_pack = struct.pack('>f', value )
	hex_value = ''.join('%2.2x' % ord( c ) for c in hex_pack )
	return hex_value


def get_blendshapes( mesh, vertices, progress_dlg ):
	"""
	Get the blendshapes from the mesh and update the vert_dict

	*Arguments:*
		* ``mesh`` The fbx mesh node
		# ``vertices`` List of vert_infos
		# ``progress_dlg`` dialog object

	*Keyword Arguments:*
		* ``none``

	*Returns:*
		* ``blendshapes`` dictionary of vert indices and their offset position values

	*Author:*
		* Randall Hess,   11/19/2013 8:52:13 PM
	"""

	#blendshapes = [ ]
	blendshapes = { }

	# get the transform used to orient and scale the vertices
	vertex_transform = compute_vertex_transform( mesh )
	if IS_3DSMAX:
		vert_xform_rows = [ vertex_transform.GetRow( 0 ), vertex_transform.GetRow( 2 ), vertex_transform.GetRow( 1 ), vertex_transform.GetRow( 3 ) ]
	else:
		vert_xform_rows = [ vertex_transform.GetRow( 0 ), -vertex_transform.GetRow( 2 ), -vertex_transform.GetRow( 1 ), vertex_transform.GetRow( 3 ) ]

	lmesh = mesh.GetNodeAttribute( )
	num_blendshape_deformers = lmesh.GetDeformerCount(FbxCommon.FbxDeformer.eBlendShape)
	if DEBUG_BLENDSHAPES:
		print '  Deformers: {0}'.format( num_blendshape_deformers )
	for blendshape_index in range( num_blendshape_deformers ):
		blendshape = lmesh.GetDeformer( blendshape_index, FbxCommon.FbxDeformer.eBlendShape )
		if DEBUG_BLENDSHAPES:
			print '  Blendshape: {0}'.format( blendshape.GetName( ) )

		num_blendshape_channels = blendshape.GetBlendShapeChannelCount( )
		if DEBUG_BLENDSHAPES:
			print '   Num BlendShape Channels: {0}'.format( num_blendshape_channels )

		for blendshape_channel_index in range( num_blendshape_channels ):
			blendshape_channel = blendshape.GetBlendShapeChannel( blendshape_channel_index )
			if DEBUG_BLENDSHAPES:
				print '   -------------------------------------------------------- '
				print '   Blendshape Channel: {0}'.format( blendshape_channel.GetName( ) )

			num_target_shapes = blendshape_channel.GetTargetShapeCount( )
			shape_dict = { }
			for target_shape_index in range( num_target_shapes ):
				target_blendshape = blendshape_channel.GetTargetShape( target_shape_index )
				blendshape_name = target_blendshape.GetName( )

				# get the blendshape mapped name if found
				for key, value in BLENDSHAPE_NAMES.iteritems():
					if key == blendshape_name:
						blendshape_name = value
						break

				#if DEBUG_BLENDSHAPES:
					#print '   TargetShape: {0}'.format( blendshape.GetName( ) )

				num_control_points = target_blendshape.GetControlPointsCount( )
				control_points = target_blendshape.GetControlPoints( )
				normals = target_blendshape.GetLayer( 0 ).GetNormals( ).GetDirectArray( )

				blend_verts = { }

					#if DEBUG_BLENDSHAPES:
						#print '    Coordinates: {0}'.format( blend_pos )

				# compare the verts with the same index
				vert_index = 0
				for vert_ in vertices:

					if vert_index % 5 == 0:
							wx.Yield( )
							progress_dlg._msg.SetLabelText( 'Getting blendshape:{0} Vert:{1}'.format( blendshape_name, vert_index ) )
							progress_dlg.UpdatePulse( )

					for index in range( num_control_points ):
						#if DEBUG_BLENDSHAPES:
							#print '    Control Point: {0}'.format( index )
							#print '    Coordinates: {0}'.format( control_points[ index ] )

						blend_index = index
						matched_index = False

						# Match the index to the current or duplicated original index
						if vert_.original_index == index:
							matched_index = True
							blend_index = index
						elif vert_.index == index:
							matched_index = True
							blend_index = index


						if matched_index and not vert_.original_index == -1:
							blend_index = vert_.index

						if matched_index:
							if DEBUG_BLENDSHAPES:
								#print '    Vert:  {0}'.format ( vert_index )
								#print '    Control Point: {0} Vertice Index: {0}'.format( index, blend_index )
								vert_index += 1

							vert = control_points[ index ]

							if IS_MAYAYUP:
								vector = [ vert[0], vert[1], vert[2], vert[3] ]
								vert_converted = matrix_multiply( vert_xform_rows, vector )
								vert_x = get_scaled_value( vert_converted[0], 1 )
								vert_y = get_scaled_value( vert_converted[1], 1 )
								vert_z = get_scaled_value( vert_converted[2], 1 )
								vert_w = get_scaled_value( vert_converted[3], 1 )

							elif IS_3DSMAX:
								scale_inches_to_meters = 39.3701
								vert_x = get_scaled_value( vert[0], scale_inches_to_meters )
								vert_y = get_scaled_value( vert[1], scale_inches_to_meters )
								vert_z = get_scaled_value( vert[2], scale_inches_to_meters )
								vert_w = get_scaled_value( vert[3], scale_inches_to_meters )


							blend_pos = [ vert_x, vert_y, vert_z, vert_w ]

							# only write out verts that have different values
							if not vert_.positions == blend_pos:

								new_pos = [0,0,0]
								for component in range(0, 3):
									if not vert_.positions[component] == blend_pos[component]:
										delta = blend_pos[component] - vert_.positions[component]
										new_pos[component] = delta

								blend_pos = new_pos


								#if not vert_.positions == blend_pos:
								if DEBUG_BLENDSHAPES:
									print ''
									print '    Vert:  {0}'.format ( vert_index )
									print '    Control Point: {0} Vertice Index: {0}'.format( index, blend_index )
									print '    Base Vert:   {0}'.format( vert_.positions )
									print '    Blend Vert:  {0}'.format( blend_pos )
									#print '     ADDING Blend Vert: {0}'.format( index )
									#print '     Normal Vector: {0}'.format( normals.GetAt( index ) )

								# triangle, Normals
								normal = normals.GetAt( index )

								if IS_MAYAYUP:
									vector = [ normal[0], normal[1], normal[2], normal[3] ]
									norm_converted = matrix_multiply( vert_xform_rows, vector )
									norm_x = get_scaled_value( norm_converted[ 0 ], 1.0 )
									norm_y = get_scaled_value( norm_converted[ 1 ], 1.0 )
									norm_z = get_scaled_value( norm_converted[ 2 ], 1.0 )
									norm_w = get_scaled_value( norm_converted[ 3 ], 1.0 )

								elif IS_3DSMAX:
									norm_x = get_scaled_value( normal[ 0 ], 1.0 )
									norm_y = get_scaled_value( normal[ 1 ], 1.0 )
									norm_z = get_scaled_value( normal[ 2 ], 1.0 )
									norm_w = get_scaled_value( normal[ 3 ], 1.0 )

								new_normal = [ norm_x, norm_y, norm_z, norm_w ]

								delta_normal = [0,0,0]

								# Normals are busted.  Just spit out zeroes.
								#for component in range(0, 3):
									#delta_normal = new_normal[component] - vert_.normal[component]

								blend_verts[ blend_index ] = [ blend_pos, delta_normal ]

			blendshapes[ blendshape_name ] = blend_verts

	return blendshapes


def get_boneweights( mesh, vertices, in_bones, progress_dlg ):
	"""
	Get the bone weight values from the mesh and update the vert_dict

	*Arguments:*
		* ``mesh`` The fbx mesh node
		# ``vertices`` List of vert_infos

	*Keyword Arguments:*
		* ``none``

	*Returns:*
		* ``bone_weights`` dictionary of verts and their bone/weight values

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   11/19/2013 8:52:13 PM
	"""

	bone_weights = { }
	for vert in vertices:
		bone_weights[ vert.index ] = { }

	do_pulse_update = len( vertices ) > 500

	bones = {}

	number_skin_deformers= mesh.GetDeformerCount( FbxCommon.FbxDeformer.eSkin )
	for skin_index in range( number_skin_deformers ):
		cluster_count = mesh.GetDeformer( skin_index, FbxCommon.FbxDeformer.eSkin ).GetClusterCount( )
		for cluster_index in range( cluster_count ):
			cluster = mesh.GetDeformer( skin_index, FbxCommon.FbxDeformer.eSkin ).GetCluster( cluster_index )

			# get the current bone/link name
			bone_name = None
			if cluster.GetLink( ):

				# associate the link/bone with an already found bone_node
				found_bone = False
				bone_node = cluster.GetLink( )
				for bone in in_bones:
					if bone.node == bone_node:
						bone_name = bone.name
						found_bone = True
						break

				if not found_bone:
					bone_name = cluster.GetLink( ).GetName( )

				# store off the current bone
				bone_key = None
				try:
					bone_key = bones[ bone_name ]
				except KeyError:
					pass

				if not bone_key:
					bones[ bone_name ] =  cluster.GetLink( )

				#lIndexCount = cluster.GetControlPointIndicesCount()
				lIndices = cluster.GetControlPointIndices( )
				lWeights = cluster.GetControlPointWeights( )

				# update the bone_weights with the associated bone & weight/values
				index = 0
				for indice in lIndices:

					if do_pulse_update:
						if index % 5 == 0:
							wx.Yield( )
							progress_dlg._msg.SetLabelText( 'Getting bone cluster:{0} Vert:{1}'.format( cluster_index, index ) )
							progress_dlg.UpdatePulse( )

					for vert in vertices:
						if vert.index == indice:
							if DEBUG_WEIGHTS:
								print 'Vert index {0} is indice: {1}'.format( vert.index, indice )
								print ' weighting vert {0} bone {1} weight {2}'.format( vert.index, bone_name, lWeights[ index ] )
							bone_weights[ indice ][ bone_name ] = lWeights[ index ]

						elif not vert.original_index == -1 and vert.original_index == indice:
							if DEBUG_WEIGHTS:
								print 'Vert original index {0} is indice: {1}'.format( vert.index, indice )
								print ' weighting vert {0} bone {1} weight {2}'.format( vert.index, bone_name, lWeights[ index ] )
							bone_weights[ vert.index ][ bone_name ] = lWeights[ index ]
					index += 1

	# print out the vert_dict
	assert isinstance( bone_weights, dict )

	if DEBUG_WEIGHTS:
		print '\n----------------'
		print 'Vertex Weights'
		print '----------------'
		for key, value in bone_weights.iteritems( ):
			print ' vert: {0}    weights: {1}'.format( key, value )
		print '\n'

	return bone_weights, bones


def matrix_multiply( matrix, vector ):
	"""
	Matrix multiply a vector
	found online, stack overflow i think :/

	*Arguments:*
		* ``matrix`` matrix
		* ``vector`` vector to multiply

	*Keyword Arguments:*
		* ``none``

	*Returns:*
		* ``vector`` vector after being multiplied by a transform matrix

	*Author:*
		* Randall Hess, randall.hess@volition-inc.com, 4/28/2014 10:03:55 PM
	"""

	rows = len( matrix )
	w = [0]*rows
	irange = range( len( vector ) )
	sum = 0
	for j in range( rows ):
		r = matrix[j]
		for i in irange:
			sum += r[i]*vector[i]
		w[j],sum = sum,0
	return w


def get_mesh_data( mesh, progress_dlg ):
	"""
	Get the face and normal data

	*Arguments:*
		* ``mesh`` FBX mesh

	*Keyword Arguments:*
		* ``none``

	*Returns:*
		* ``face_data`` List of face_info objects that contain face index, uvs, norms, verts

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   12/6/2013 3:02:30 PM
	"""

	face_data = [ ]

	if DEBUG_OUTPUT:
		print '---------------------------------------------------------------------------'
		print 'Faces\n'

	# TODO - Handle Multiple Layers
	lmesh = mesh.GetNodeAttribute( )
	layer_element = lmesh.GetLayer( 0 )
	if layer_element:

		# get the transform used to orient and scale the vertices
		vertex_transform = compute_vertex_transform( mesh )
		#3dsmax
		if IS_3DSMAX:
			vert_xform_rows = [ vertex_transform.GetRow( 0 ), vertex_transform.GetRow( 2 ), vertex_transform.GetRow( 1 ), vertex_transform.GetRow( 3 ) ]
		else:
			vert_xform_rows = [ vertex_transform.GetRow( 0 ), -vertex_transform.GetRow( 2 ), -vertex_transform.GetRow( 1 ), vertex_transform.GetRow( 3 ) ]

		# setup the vert data
		vertices = [ ]
		num_verts = lmesh.GetControlPointsCount( )
		for i in range( num_verts ):
			vertices.append( Vertex_Info( i ) )

		# get the fbx verts
		fbx_verts = [ ]
		control_points = lmesh.GetControlPoints( )
		for vert_index in range( num_verts ):
			wx.Yield( )
			vert = control_points[ vert_index ]

			if IS_MAYAYUP:
				vector = [ vert[0], vert[1], vert[2], vert[3] ]
				vert_converted = matrix_multiply( vert_xform_rows, vector )
				vert_x = get_scaled_value( vert_converted[0], 1 )
				vert_y = get_scaled_value( vert_converted[1], 1 )
				vert_z = get_scaled_value( vert_converted[2], 1 )
				vert_w = get_scaled_value( vert_converted[3], 1 )

			elif IS_3DSMAX:
				scale_inches_to_meters = 39.3701
				vert_x = get_scaled_value( vert[0], scale_inches_to_meters )
				vert_y = get_scaled_value( vert[1], scale_inches_to_meters )
				vert_z = get_scaled_value( vert[2], scale_inches_to_meters )
				vert_w = get_scaled_value( vert[3], scale_inches_to_meters )

			fbx_verts.append( [ vert_x, vert_y, vert_z, vert_w ] )

		# get the uv channel name
		uv_elements = layer_element.GetUVSets( )
		uv_name = ''
		for uv_element in uv_elements:
			if uv_element:
				uv_name = uv_element.GetName( )

		# get the material element in the layer
		material_element = layer_element.GetMaterials( )

		# get the face data
		triangle_count = lmesh.GetPolygonVertexCount( ) / 3
		for triangle_index in range( triangle_count):

			# only update the pulse in increments of 5
			if triangle_index % 5 == 0:
				wx.Yield( )
				progress_dlg._msg.SetLabelText( 'Getting Mesh Triangle: {0}'.format( triangle_index ) )
				progress_dlg.UpdatePulse( )

			# create the face object
			face = Face_Info( triangle_index )

			# get the material id for the current face
			if material_element:
				material_id = material_element.GetIndexArray( ).GetAt( triangle_index )
				face.material_id = material_id

			for idx in range( 0, 3 ):

				# triangle, Vertices
				index = lmesh.GetPolygonVertex( triangle_index, idx )
				if index == -1:
					return None, None
				face.indices[ idx ] = index

				# setup a temp info
				temp_vert = Vertex_Info( index )
				temp_vert.index = index
				temp_vert.positions[ 0 ] = fbx_verts[ index ][ 0 ]
				temp_vert.positions[ 1 ] = fbx_verts[ index ][ 1 ]
				temp_vert.positions[ 2 ] = fbx_verts[ index ][ 2 ]

				# triangle, Normals
				fbx_norm = FbxCommon.FbxVector4()
				lmesh.GetPolygonVertexNormal( triangle_index, idx, fbx_norm )

				if IS_MAYAYUP:
					vector = [ fbx_norm[0], fbx_norm[1], fbx_norm[2], fbx_norm[3] ]
					norm_converted = matrix_multiply( vert_xform_rows, vector )
					temp_vert.normal[ 0 ] = get_scaled_value( norm_converted[ 0 ], 1.0 )
					temp_vert.normal[ 1 ] = get_scaled_value( norm_converted[ 1 ], 1.0 )
					temp_vert.normal[ 2 ] = get_scaled_value( norm_converted[ 2 ], 1.0 )

				elif IS_3DSMAX:
					temp_vert.normal[ 0 ] = get_scaled_value( fbx_norm[ 0 ], 1.0 )
					temp_vert.normal[ 1 ] = get_scaled_value( fbx_norm[ 1 ], 1.0 )
					temp_vert.normal[ 2 ] = get_scaled_value( fbx_norm[ 2 ], 1.0 )

				# triangle, UVs
				tex_coord_found = False
				fbx_uv = FbxCommon.FbxVector2()
				tex_coord_found = lmesh.GetPolygonVertexUV( triangle_index, idx, uv_name, fbx_uv )
				temp_vert.uvs[ 0 ] = get_scaled_value( fbx_uv[ 0 ], 1.0 )

				# This may be 3dsmax only conversion
				temp_vert.uvs[ 1 ] = 1.0 - ( get_scaled_value( fbx_uv[ 1 ], 1.0 ) )

				# set the vertex indice with the current vert_info
				if vertices[ index ].index == -1:
					vertices[ index ] = temp_vert
					vertices[ index ].original_index = index

				else:
					# if the vert is set make sure the positions,norms and uvs are all the same
					if not vertices[ index ].positions == temp_vert.positions or \
					   not vertices[ index ].normal == temp_vert.normal or \
					   not vertices[ index ].uvs == temp_vert.uvs:

						# try to find a similar vert with the same old index
						found_vert = None
						for vert in vertices:
							if vert.original_index == index:
								if vert.positions == temp_vert.positions and vert.normal == temp_vert.normal and vert.uvs == temp_vert.uvs:
									found_vert = vert
									temp_vert = vert
									break

						if found_vert is None:
							# create a new vert
							temp_index = len( vertices) + 1
							temp_vert.index = temp_index
							temp_vert.original_index = index
							vertices.append( temp_vert )
							if DEBUG_OUTPUT or DEBUG_VERTS:
								print 'Duplicating vert: {0} New indice: {1}'.format( index, temp_index )

					else:
						temp_vert.index = index
						vertices[ index ] = temp_vert

				# set the face vert data
				face.verts[ idx ] = temp_vert

			# Output
			if DEBUG_OUTPUT:
				print '***************************************'
				print 'Face: {0}'.format( face.index )
				print '  Indices: {0}'.format( face.indices )
				index = 0
				for vert in face.verts:
					print '  Vert {0}: {1}'.format( index, vert.positions )
					index += 1
				index = 0
				for vert in face.verts:
					print '  UV {0}: {1}'.format( index, vert.uvs )
					index += 1
				print '***************************************'

			# update the face structure
			face_data.append( face )

		return face_data, vertices


def get_fbx_materials( mesh ):
	"""
	Get the materials from the mesh

	*Arguments:*
		* ``mesh`` Fbx mesh

	*Keyword Arguments:*
		* ``none``

	*Returns:*
		* ``materials`` list of materials

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   11/19/2013 9:40:49 PM
	"""

	materials = [ ]
	material_count = 0

	node = None
	if mesh:
		node = mesh.GetNode()
		if node:
			material_count = node.GetMaterialCount()

			for layer_index in range( mesh.GetLayerCount( ) ):
				layer_element_material = mesh.GetLayer( layer_index ).GetMaterials()
				if layer_element_material:
					if layer_element_material.GetReferenceMode() == FbxCommon.FbxLayerElement.eIndex:
						#Materials are in an undefined external table
						continue

					if material_count > 0:
						color = FbxCommon.FbxColor()

						if DEBUG_OUTPUT:
							print " Materials on layer {0}".format( layer_index )

						for mat_count in range(material_count):
							if DEBUG_OUTPUT:
								print "  Material {0} ".format( mat_count )

							material = node.GetMaterial(mat_count)
							material_name = material.GetName( )
							materials.append( material )

	return materials


def load_fbx_scene( fbx_scene, do_3dsmax, do_Maya ):
	"""
	Load the FBX scene and do necessary conversions

	*Arguments:*
		* ``fbx_scene`` Fbx scene file

	*Keyword Arguments:*
		* ``none``

	*Returns:*
	   * ``lStatus`` Status of opening the fbx_scene
		* ``lScene`` Initialized fbx_scene
		* ``lSdkManager`` Fbx sdkManager

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   11/19/2013 9:49:55 PM
	"""

	# Prepare the FBX SDK.
	lSdkManager, lScene = FbxCommon.InitializeSdkObjects( )

	if fbx_scene:
		lStatus = FbxCommon.LoadScene(lSdkManager, lScene, fbx_scene)

	else:
		lStatus = False
		print("\n\nUsage: ImportScene <FBX file name>\n")

	if not lStatus:
		print("\n\nAn error occurred while loading the scene...")
		return False

	else:
		# Get fbx scene units/axis
		fbx_scene_axis = lScene.GetGlobalSettings( ).GetAxisSystem( )
		fbx_scene_units = lScene.GetGlobalSettings().GetSystemUnit()

				# override with force settings
		#if do_Maya:
			#fbx_scene_axis = FbxCommon.FbxAxisSystem.MayaYUp
			#SCENE_SCALE_CONVERSION = 0.01
		if do_3dsmax:
			max_scene_axis = FbxCommon.FbxAxisSystem.Max
			#SCENE_SCALE_CONVERSION = fbx_scene_units.GetScaleFactor( ) * 0.01
			max_scene_axis.ConvertScene( lScene  )
			#max_scene_axis.ConvertChildren( lScene.GetRootNode(), max_scene_axis )
			#new_system_unit = FbxCommon.FbxSystemUnit.Inch
			#new_system_unit.ConvertScene( lScene )
			#SCENE_SCALE_CONVERSION = 0.01

		# GetScaleFactor gets the system units converted to cm, convert those to meters for game
		global SCENE_SCALE_CONVERSION
		SCENE_SCALE_CONVERSION = fbx_scene_units.GetScaleFactor( ) * 0.01

		# vector sign, indicates pos or neg direction of the axis
		up_vector_sign 	= 0
		front_vector_sign = 1
		front_vector_type = FbxCommon.FbxAxisSystem.eParityOdd

		# maya
		if fbx_scene_units.GetScaleFactor( ) == 1.0:
			SCENE_SCALE_CONVERSION = 0.01

		# Convert the axis system
		# grab the up vector
		# GetFrontVector is missing from Fbx Python SDK -2014.1, Should be there in 2014.2
		#fbxAxis.GetFrontVector( front_vector_sign )
		up_vector_type, up_vector_sign = fbx_scene_axis.GetUpVector( )
		coordinate_system_type	= fbx_scene_axis.GetCoorSystem( )

		up_vector		= FbxCommon.FbxVector4( )
		front_vector	= FbxCommon.FbxVector4( )
		right_vector	= FbxCommon.FbxVector4( )

		if up_vector_type == FbxCommon.FbxAxisSystem.eXAxis:
			up_vector.Set( 1.0, 0.0, 0.0, 0.0 )
			if front_vector_type == FbxCommon.FbxAxisSystem.eParityEven:
				front_vector.Set(0.0, 1.0, 0.0, 0.0 )
				right_vector.Set(0.0, 0.0, 1.0, 0.0 )
			else:
				front_vector.Set(0.0, 0.0, 1.0, 0.0 )
				right_vector.Set(0.0, 1.0, 0.0, 0.0 )

		elif up_vector_type == FbxCommon.FbxAxisSystem.eYAxis:
			up_vector.Set( 0.0, 1.0, 0.0, 0.0 )
			if front_vector_type == FbxCommon.FbxAxisSystem.eParityEven:
				front_vector.Set(1.0, 0.0, 0.0, 0.0 )
				right_vector.Set(0.0, 0.0, 1.0, 0.0 )
			else:
				front_vector.Set( 0.0, 0.0, 1.0, 0.0 )
				right_vector.Set( 1.0, 0.0, 0.0, 0.0 )

		elif up_vector_type == FbxCommon.FbxAxisSystem.eZAxis:
			up_vector.Set( 0.0, 0.0, 1.0, 0.0)
			if front_vector_type == FbxCommon.FbxAxisSystem.eParityEven:
				front_vector.Set( 1.0, 0.0, 0.0, 0.0 )
				right_vector.Set( 0.0, 1.0, 0.0, 0.0 )
			else:
				front_vector.Set( 0.0, 1.0, 0.0, 0.0 )
				right_vector.Set( 1.0, 0.0, 0.0, 0.0 )
		else:
			pass

		up_vector		*= float( up_vector_sign )
		front_vector	*= float( front_vector_sign )

		coordinate_system_transform = FbxCommon.FbxMatrix( )



		#REPLACING THIS CHECK NOW THAT WE ARE CONVERTING TO MAX Axis
		if fbx_scene_axis == FbxCommon.FbxAxisSystem.MayaYUp:
			global IS_MAYAYUP
			IS_MAYAYUP = True

			# construct the axis
			right_vector.Set( 1.0, 0.0, 0.0, 0.0)
			front_vector.Set( 0.0, 0.0, 1.0, 0.0)
			up_vector.Set( 0.0, 1.0, 0.0, 0.0 )

			# create the coord sys transform
			coordinate_system_transform.SetColumn( 0, right_vector )	#RVec
			coordinate_system_transform.SetColumn( 1, -up_vector )	#UVec
			coordinate_system_transform.SetColumn( 2, front_vector )	#FVec
			coordinate_system_transform.SetColumn( 3, FbxCommon.FbxVector4( ) )	#Position

		elif fbx_scene_axis == FbxCommon.FbxAxisSystem.Max:
			global IS_3DSMAX
			IS_3DSMAX = True

			# create the coord sys transform
			coordinate_system_transform.SetColumn( 0, -right_vector )	#RVec
			coordinate_system_transform.SetColumn( 1, up_vector )			#UVec
			coordinate_system_transform.SetColumn( 2, front_vector )		#FVec
			coordinate_system_transform.SetColumn( 3, FbxCommon.FbxVector4( ) )	#Position

		if do_3dsmax:
			global IS_MAYAYUP
			IS_MAYAYUP = False

			global IS_3DSMAX
			IS_3DSMAX = True

			right_vector.Set( 1.0, 0.0, 0.0, 0.0)
			front_vector.Set( 0.0, 1.0, 0.0, 0.0)
			up_vector.Set( 0.0, 0.0, 1.0, 0.0 )

			coordinate_system_transform.SetColumn( 0, -right_vector )	#RVec
			coordinate_system_transform.SetColumn( 1, up_vector )	#UVec
			coordinate_system_transform.SetColumn( 2, front_vector )	#FVec
			coordinate_system_transform.SetColumn( 3, FbxCommon.FbxVector4( ) )	#Position

		# get the scale matrix
		scale_matrix = FbxCommon.FbxMatrix( )
		scale_matrix.SetIdentity( )
		scale_col0 = scale_matrix[0]
		scale_col1 = scale_matrix[1]
		scale_col2 = scale_matrix[2]

		rvec = FbxCommon.FbxVector4( )
		rvec.Set( SCENE_SCALE_CONVERSION, scale_col0[1], scale_col0[2], scale_col0[3] )
		uvec = FbxCommon.FbxVector4( )
		uvec.Set( scale_col1[0], SCENE_SCALE_CONVERSION, scale_col1[2], scale_col1[3] )
		fvec = FbxCommon.FbxVector4( )
		fvec.Set( scale_col2[0], scale_col2[1], SCENE_SCALE_CONVERSION, scale_col2[3] )

		scale_matrix.SetColumn( 0, rvec )
		scale_matrix.SetColumn( 1, uvec )
		scale_matrix.SetColumn( 2, fvec )

		coordinate_system_transform = coordinate_system_transform * scale_matrix

		# This matrix needs to be inverted/transposed for the math to work throughout the cruncher.
		coordinate_system_transform.Transpose( )
		global COORD_SYS_TRANSFORM
		COORD_SYS_TRANSFORM = coordinate_system_transform

		return lStatus, lScene, lSdkManager

	return False, None


def remove_transform_scale( object_transform ):
	"""
	Remove any scale values from the object transform

	*Arguments:*
		* ``object_transform`` transform of an object

	*Keyword Arguments:*
		* ``none``

	*Returns:*
		* ``out_matrix`` matrix without any scale values

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   11/19/2013 9:54:14 PM
	"""

	# Break Down the Matrix
	#translation = FbxVector4( )
	#quat = FbxQuaternion( )
	#shear = FbxVector4( )
	#scale = FbxVector4( )
	#object_transform.GetElements( translation, quat, shear, scale )

	## Convert to an AffineMatrix
	#object_affine_transform = FbxAMatrix( )
	#object_affine_transform.SetTQS( translation, quat, scale )

	# get the scale matrix
	scale_matrix = FbxCommon.FbxAMatrix( )
	scale_matrix.SetIdentity( )
	scale_col0 = scale_matrix[0]
	scale_col1 = scale_matrix[1]
	scale_col2 = scale_matrix[2]

	# build up the vectors with the scale conversion
	rvec = FbxCommon.FbxVector4( )
	rvec.Set( SCENE_SCALE_CONVERSION, scale_col0[1], scale_col0[2], scale_col0[3] )
	uvec = FbxCommon.FbxVector4( )
	uvec.Set( scale_col1[0], SCENE_SCALE_CONVERSION, scale_col1[2], scale_col1[3] )
	fvec = FbxCommon.FbxVector4( )
	fvec.Set( scale_col2[0], scale_col2[1], SCENE_SCALE_CONVERSION, scale_col2[3] )

	# build a temp regular matrix
	temp_matrix = FbxCommon.FbxMatrix( )
	temp_matrix.SetColumn( 0, rvec )
	temp_matrix.SetColumn( 1, uvec )
	temp_matrix.SetColumn( 2, fvec )

	# break down the temp matrix and convert to AffineMatrix that we can multiply
	translation = FbxCommon.FbxVector4( )
	quat = FbxCommon.FbxQuaternion( )
	shear = FbxCommon.FbxVector4( )
	scale = FbxCommon.FbxVector4( )
	temp_matrix.GetElements( translation, quat, shear, scale )
	scale_matrix.SetTQS( translation, quat, scale )
	out_matrix = object_transform * scale_matrix

	return out_matrix

def compute_vertex_transform( node ):
	"""
	NOTE STL 2014/02/05 It seems that FBX of vertices are in scene space, rather than being local to their node.  For whatever
	reason, it appears that the geometric transform of the node is capable of putting the vertices back into local space WITHOUT
	inversion.  Since Volition vectors are placed on the left side of a matrix multiplication, the geometric transform is applied first.
	The last transform simply handles scale and axis conversions from the tool coordinate system to the Volition coordinate system.  We
	want the vertices to be transformed in this way because then any calculations done with them will be in the Volition coordinate
	system as well.

	*Arguments:*
		* ``fbx_node`` the current fbx object

	*Keyword Arguments:*
		* ``Argument`` Enter a description for the keyword argument here.

	*Returns:*
		* ``Value`` If any, enter a description for the return value here.

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess, 4/19/2014 11:30:42 PM
	"""

	# Get the "geometric" transformation.
	geometric_translation   = FbxCommon.FbxVector4( )
	geometric_rotation      = FbxCommon.FbxVector4( )
	geometric_scale         = FbxCommon.FbxVector4( )
	geometric_transform_fbx = FbxCommon.FbxMatrix( )

	geometric_translation = node.GetGeometricTranslation( FbxCommon.FbxNode.eSourcePivot )
	geometric_rotation    = node.GetGeometricRotation( FbxCommon.FbxNode.eSourcePivot )
	geometric_scale       = node.GetGeometricScaling( FbxCommon.FbxNode.eSourcePivot )
	geometric_transform_fbx.SetTRS( geometric_translation, geometric_rotation, geometric_scale )

	# Volition multiplication goes from left to right.  This will put the object transform matrix into our coordinate system.
	vertex_transform = geometric_transform_fbx * COORD_SYS_TRANSFORM
	return vertex_transform


def compute_world_transform( fbx_node, use_geom = False ):
	"""
	Taken from rlb_import_fbx_mesh.cpp
	Returns the world transform for an fbx node object.
	This includes converting it to a friendly Volition format, and accounting for a pivot offset and export origin

	*Arguments:*
		* ``fbx_node`` the current fbx object

	*Keyword Arguments:*
		* ``use_geom`` bool to use the geometry transform instead of coordinate_system_transform

	*Returns:*
		* ``out_matrix`` The world transform matrix for the given object

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   8/19/2013 5:52:50 PM
	"""

	fbx_global_transform = fbx_node.EvaluateGlobalTransform()

	# Get the offset transformation
	geometric_translation = fbx_node.GetGeometricTranslation( FbxCommon.FbxNode.eSourcePivot )
	geometric_rotation    = fbx_node.GetGeometricRotation( FbxCommon.FbxNode.eSourcePivot )
	geometric_scale       = fbx_node.GetGeometricScaling( FbxCommon.FbxNode.eSourcePivot )

	# Pivot offset
	geometric_transform = FbxCommon.FbxAMatrix( )
	geometric_transform.SetTRS( geometric_translation, geometric_rotation, geometric_scale )

	# Fbx Matrix multiplication goes from right to left, Pivot Offset +
	object_transform = fbx_global_transform * geometric_transform

	if not use_geom:
		object_transform = fbx_global_transform

	# Break Down the Matrix
	translation = FbxCommon.FbxVector4( )
	quat = FbxCommon.FbxQuaternion( )
	shear = FbxCommon.FbxVector4( )
	scale = FbxCommon.FbxVector4( )
	COORD_SYS_TRANSFORM.GetElements( translation, quat, shear, scale )

	# Convert to an AffineMatrix
	coord_sys_transA = FbxCommon.FbxAMatrix( )
	coord_sys_transA.SetTQS( translation, quat, scale )

	# Inverse the coordsys transform
	coordinate_system_inverse = coord_sys_transA.Inverse( )

	# Volition multiplication goes from left to right.  This will put the object transform matrix into our coordinate system
	out_matrix = coord_sys_transA * object_transform * coordinate_system_inverse

	return out_matrix


def get_node_properties( fbx_object, property_name = None, get_value = False ):
	"""
	Get specific attributes off of an Fbx node

	*Arguments:*
		* ``fbx_object`` fbx object

	*Keyword Arguments:*
		* ``property_name`` the attribute/property we are looking for
		* ``get_value`` bool if we want to return a generic value

	*Returns:*
		* ``Value`` If any, enter a description for the return value here.

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   11/22/2013 8:41:09 AM
	"""

	if property_name is None:
		return False

	property_count = 0
	#lTitleStr = "    Property Count: "

	fbx_property = fbx_object.GetFirstProperty( )
	while fbx_property.IsValid( ):
		if fbx_property.GetFlag( FbxCommon.FbxPropertyAttr.eUserDefined ):
			property_count += 1

		fbx_property= fbx_object.GetNextProperty( fbx_property )

	if property_count == 0:
		return # there are no user properties to display

	#DisplayInt(lTitleStr, property_count)

	fbx_property = fbx_object.GetFirstProperty( )
	i = 0
	while fbx_property.IsValid( ):
		if fbx_property.GetFlag( FbxCommon.FbxPropertyAttr.eUserDefined ):

			if fbx_property.GetName( ) == property_name:
				lPropertyDataType= fbx_property.GetPropertyDataType( )
				if not get_value:
					return lPropertyDataType

				lPropertyDataType= fbx_property.GetPropertyDataType( )

				# BOOL
				if lPropertyDataType.GetType() == FbxCommon.eFbxBool:
					fbx_property = FbxCommon.FbxPropertyBool1( fbx_property)
					val = fbx_property.Get( )
					return val

				# REAL
				elif lPropertyDataType.GetType() == FbxCommon.eFbxDouble:
					fbx_property = FbxCommon.FbxPropertyDouble1( fbx_property)
					val = fbx_property.Get( )
					return val

				# FLOAT
				elif lPropertyDataType.GetType() == FbxCommon.eFbxFloat:
					fbx_property = FbxCommon.FbxPropertyFloat1( fbx_property )
					val = fbx_property.Get( )
					return val

				# COLOR
				#elif lPropertyDataType.Is(DTColor3) or lPropertyDataType.Is(DTColor4):
					#val = fbx_property.Get()
					#lDefault=FbxGet <FbxColor> (fbx_property)
					#sprintf(lBuf, "R=%f, G=%f, B=%f, A=%f", lDefault.mRed, lDefault.mGreen, lDefault.mBlue, lDefault.mAlpha)
					#DisplayString("            Default Value: ", lBuf)
				#    pass

				# INTEGER
				elif lPropertyDataType.GetType( ) == FbxCommon.eFbxInt:
					fbx_property = FbxCommon.FbxPropertyInteger1( fbx_property )
					val = fbx_property.Get( )
					return val

				# VECTOR
				elif lPropertyDataType.GetType( ) == FbxCommon.eFbxDouble3:
					fbx_property = FbxCommon.FbxPropertyDouble3( fbx_property )
					val = fbx_property.Get( )
					lBuf = "X=%f, Y=%f, Z=%f", (val[0], val[1], val[2])
					return val

				# DOUBLE4
				elif lPropertyDataType.GetType( ) == FbxCommon.eFbxDouble4:
					fbx_property = FbxCommon.FbxPropertyDouble4( fbx_property )
					val = fbx_property.Get( )
					lBuf = "X=%f, Y=%f, Z=%f, W=%f", (val[0], val[1], val[2], val[3])
					return val

				# STRING
				elif lPropertyDataType.GetType( ) == FbxCommon.eFbxString:
					fbx_property = FbxCommon.FbxPropertyString( fbx_property )
					val = fbx_property.Get( )
					return val

				# LIST
				#elif lPropertyDataType.GetType() == eFbxEnum:
				#val = fbx_property.Get()

				# UNIDENTIFIED
				else:
					pass
					#DisplayString("            Default Value: UNIDENTIFIED")
			i += 1

		fbx_property= fbx_object.GetNextProperty( fbx_property )



class Label_Ctrl(wx.Panel):
	"""
	Custom text control
	Using as a label of sorts at the moment

	*Arguments:*
		* ``parent`` wx parent id

	*Keyword Arguments:*
		* ``text_string`` What to show in the text control
		* ``boxSize`` Size of the text ctrl box
		* ``onTop`` Show ctrl on top

	*Author:*
		* Randall Hess, , 1/2/2014 3:03:53 PM
	"""

	def __init__(self, parent, text_string = "", boxSize=(200, 10), onTop = True):
		wx.Panel.__init__(self, parent)

		self.the_text = wx.TextCtrl(self, -1, text_string, size=boxSize, style=wx.TE_READONLY)


	def set_text(self, text):
		"""
		Update the text control label

		*Arguments:*
			* ``text`` String to show in the label

		*Author:*
			* Randall Hess, , 1/2/2014 3:06:09 PM
		"""

		self.the_text.SetLabel(text)



class Table_Data( gridlib.PyGridTableBase ):
	"""
	Grid table data for the Material Grid
	copied mostly from the Docs and Demos

	*Arguments:*
		* ``None``

	*Author:*
		* Randall Hess, , 1/2/2014 3:07:43 PM
	"""

	def __init__( self, shader_names ):
		gridlib.PyGridTableBase.__init__( self )
		self.shader_names = shader_names
		self.colLabels = [ 'ID', 'Material', 'Shader' ]
		self.choice_types = self.get_shader_choices( )
		self.data_types = [ gridlib.GRID_VALUE_NUMBER,
					           gridlib.GRID_VALUE_STRING,
					           gridlib.GRID_VALUE_CHOICE + self.choice_types,
					           ]

		self.data = [ ]
		num_rows = 10
		for i in range( 0, num_rows ):
			a_list = [ i, '', '' ]
			self.data.append( a_list )


	def get_shader_choices( self ):
		"""
		Get the list of shader types from the xml shaders file
		Populate the choice list with the shader names

		*Arguments:*
			* ``None``

		*Keyword Arguments:*
			* ``None``

		*Returns:*
			* ``list`` List containing a single string list of shader names

		*Author:*
			* Randall Hess, , 1/3/2014 1:51:38 PM
		"""

		shader_types = ':'
		for shader in self.shader_names:
			shader_types += shader + ','

		return shader_types


	def GetNumberRows( self ):
		"""
		Get the number of rows in the grid

		*Arguments:*
			* ``None``

		*Keyword Arguments:*
			* ``None``

		*Returns:*
			* ``int`` number of rows in the grid

		*Author:*
			* Randall Hess, , 1/2/2014 3:10:59 PM
		"""

		return len( self.data )


	def GetNumberCols( self ):
		"""
		Get the number of columns in the grid

		*Arguments:*
			* ``None``

		*Keyword Arguments:*
			* ``None``

		*Returns:*
			* ``int`` number of columns in the grid

		*Author:*
			* Randall Hess, , 1/2/2014 3:11:48 PM
		"""

		return len( self.data[0] )


	def IsEmptyCell( self, row, col ):
		"""
		Does the grid cell have a value

		*Arguments:*
			* ``row`` Grid row int
			* ``col`` Grid column int

		*Returns:*
			* ``Bool`` Is the cell empty

		*Author:*
			* Randall Hess, , 1/2/2014 3:16:01 PM
		"""

		try:
			return not self.data[ row ][ col ]
		except IndexError:
			return True


	def GetValue( self, row, col ):
		"""
		Return the value of the grid cell

		*Arguments:*
			* ``row`` Grid row int
			* ``col`` Grid column int

		*Returns:*
			* ``string`` string of the cell data

		*Author:*
			* Randall Hess, , 1/2/2014 3:17:01 PM
		"""

		try:
			return self.data[ row ][ col ]
		except IndexError:
			return ''


	def SetValue( self, row, col, value ):
		"""
		Set the value of the grid cell

		*Arguments:*
			* ``row`` Grid row int
			* ``col`` Grid column int
			* ``value`` Value to set the cell

		*Returns:*
			* ``None``

		*Author:*
			* Randall Hess, , 1/2/2014 3:17:01 PM
		"""

		def innerSetValue( row, col, value ):
			try:
				self.data[ row ][ col ] = value
			except IndexError:
				pass

		innerSetValue(row, col, value)


	def GetColLabelValue( self, col ):
		"""
		Get the label string of the given column

		*Arguments:*
			* ``col`` Grid column int

		*Returns:*
			* ``string`` text of the column

		*Author:*
			* Randall Hess, , 1/2/2014 3:17:01 PM
		"""

		return self.colLabels[ col ]


	def GetTypeName( self, row, col ):
		"""
		Return the string of the cell type name

		Called to determine the kind of editor/renderer to use by
		default, doesn't necessarily have to be the same type used
		natively by the editor/renderer if they know how to convert.

		*Arguments:*
			* ``row`` Grid row int
			* ``col`` Grid column int

		*Author:*
			* Randall Hess, , 1/2/2014 3:12:41 PM
		"""

		return self.data_types[ col ]


	def CanGetValueAs( self, row, col, type_name ):
		"""
		Called to determine how the data can be fetched and stored by the
		editor and renderer.  This allows you to enforce some type-safety
		in the grid.

		*Arguments:*
			* ``row`` grid row int
			* ``col`` grid column int
			* ``type_name`` name of the grid type

		*Returns:*
			* ``bool`` can get the value as a specific type

		*Author:*
			* Randall Hess, , 1/2/2014 3:08:42 PM
		"""

		col_type = self.data_types[ col ].split(':')[0]
		if type_name == col_type:
			return True
		else:
			return False


	def CanSetValueAs(self, row, col, type_name):
		"""
		Determine if the grid cell can set a certain value type

		*Arguments:*
			* ``row`` Grid row int
			* ``col`` Grid column int
			* ``type_name`` String of the data type

		*Returns:*
			* ``Bool`` can set a value in this cell based on type

		*Author:*
			* Randall Hess, , 1/2/2014 3:14:04 PM
		"""

		return self.CanGetValueAs( row, col, type_name )



class Table_Grid( gridlib.Grid ):
	"""
	The Material Table Grid

	*Arguments:*
		* ``parent`` Id of the wx parent frame

	*Author:*
		* Randall Hess, , 1/2/2014 3:02:43 PM
	"""

	def __init__( self, parent, shader_names ):
		gridlib.Grid.__init__(self, parent, -1)
		table = Table_Data( shader_names )

		self.SetTable(table, True)
		self.SetRowLabelSize(0)
		self.SetBackgroundColour((210,184,134))


		# Hardcoding columns to fit the UI
		self.SetMargins(0,0)
		self.DisableDragCell( )
		self.DisableDragColMove( )
		self.DisableDragColSize( )
		self.DisableDragRowSize( )
		self.AutoSizeColumns(True)
		self.setup_grid( )
		gridlib.EVT_GRID_CELL_LEFT_DCLICK(self, self.OnLeftDClick)


	def setup_grid( self ):
		"""
		Setup the grid with custom settings to start out with

		*Author:*
			* Randall Hess, , 1/3/2014 2:07:28 PM
		"""

		# set custom sizes for the column widths
		col_width = 168
		self.SetColMinimalWidth( 0, 10 )
		self.SetColSize( 0, 10 )
		self.SetColMinimalWidth( 1, col_width )
		self.SetColSize( 1, col_width )
		self.SetColMinimalWidth( 2, col_width )
		self.SetColSize( 2, col_width )
		self.SetColLabelSize( 18 )

		# mark all columns as read only until data is given
		for row in range( self.GetNumberRows( ) ):
			#self.SetBackgroundColour((210,184,134))
			#self.SetForegroundColour((210,184,134))

			self.SetRowSize( row, 20 )
			for col in range( self.GetNumberCols( ) ):
				#if not col == 0:
					#self.SetCellBackgroundColour(row, col, (210,184,134))
				self.SetReadOnly( row, col, isReadOnly = True )


	def OnLeftDClick( self, event ):
		"""
		Handle Double-LeftClick

		*Arguments:*
			* ``event`` wx.Event

		*Author:*
			* Randall Hess, , 1/2/2014 3:01:11 PM
		"""

		if self.CanEnableCellControl():
			# only editing cell #2 for now, Shader reference
			if event.GetCol( ) == 2:
				# only edit if there is a value in the material cell
				if self.Table.GetValue( event.GetRow( ), 1 ):
					self.EnableCellEditControl()



class App_Frame( wx.Frame ):
	"""
	FBX Converter Frame, hold the main UI and Functionality of the APP

	*Arguments:*
		* ``parent`` wx.Parent id
		* ``ID`` wx ID of the frame

	*Keyword Arguments:*
		* ``title`` Title of the APP

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess, , 1/2/2014 2:59:47 PM
	"""

	def __init__( self, parent, ID, title='Saints Row FBX Converter - v1.05' ):
		wx.Frame.__init__(self, parent, ID, title, wx.DefaultPosition, wx.Size( 422, 800 ), style = wx.DEFAULT_DIALOG_STYLE | wx.CLIP_CHILDREN | wx.NO_FULL_REPAINT_ON_RESIZE )
		#self.SetBackgroundColour((86,54,169))
		#self.SetBackgroundColour((210,184,134))
		#self.SetBackgroundColour((140,140,140))

		global WORKING_DIR
		WORKING_DIR = os.getcwd( )
		self.version = 1.05

		# FBX Scene Data
		self.fbx_file = None
		self.coordinate_system_transform = None
		self.mesh_selection = 0
		self.config_file = 'config.ini'
		self.last_dir = None
		self.do_triangulate = True
		self.remove_temp_files = True
		self.do_3dsmax = False
		self.do_Maya = False

		self.colliders = [ ]
		self.bones = [ ]
		self.bone_orders = [ ]
		self.bone_weights = [ ]
		self.tags = [ ]
		self.vertices = [ ]
		self.meshes = [ ]
		self.mesh_names = [ ]
		self.mesh_data = [ ]
		self.materials = [ ]
		self.material_elements = { }
		self.material_names = [ ]
		self.textures = [ ]
		self.shader_names = [ ]
		self.selected_mesh = None
		self.selected_material = None
		self.rigx_file = None
		self.rigx_files = [ ]
		self.cmeshx_file = None
		self.cmeshx_files = [ ]
		self.smeshx_file = None
		self.smeshx_files = [ ]
		self.matlibx_file = None
		self.matlibx_files = [ ]
		self.morphx_file = None
		self.morphx_files = [ ]
		self.blendshapes = [ ]
		self.node_index = 0
		self.nodes = { }
		self.game_folder = None

		# Status Bar
		self.CreateStatusBar()
		self.SetStatusText( 'Status:   Import FBX File' )

		# Create Menu Items
		## FILE
		self.menu = wx.Menu()
		self.menu.Append( 100, "&Import FBX", "Import FBX File (*.FBX)" )
		#self.menu.AppendSeparator()
		#self.menu.Append( 101, "&Set Game Folder", "Set Game Folder" )
		#self.menu.Append( 102, "&Package Files", "Package files" )
		self.menu.AppendSeparator()
		self.menu.Append( 110, "&Exit", "Terminate the program" )

		## SETTINGS
		self.settings_menu = wx.Menu()
		self.settings_menu.AppendCheckItem( 202, "&Triangulate Meshes", "Triangulate Meshes" )
		self.settings_menu.Check( 202, self.do_triangulate )
		self.settings_menu.AppendCheckItem( 201, "&Remove Temp Files", "Remove Temp Files" )
		self.settings_menu.Check( 201, self.remove_temp_files )
		self.settings_menu.AppendSeparator()
		self.settings_menu.AppendCheckItem( 203, "&Force 3dsMax ZUp, In", "Force 3dsMax ZUp, In" )
		self.settings_menu.Check( 203, self.do_3dsmax )
		self.settings_menu.AppendCheckItem( 204, "&Force Maya YUp, Cm", "Force Maya YUp, Cm" )
		self.settings_menu.Check( 204, self.do_Maya )

		## HELP
		self.help_menu = wx.Menu()
		self.help_menu.Append( 300, "&Online Documentation", "Online Documentation" )
		self.help_menu.Append( 301, "&Online FAQ", "Frequently Asked Questions" )
		self.help_menu.Append( 304, "&Search Packages", "Search Packages" )
		self.help_menu.Append( 302, "&SaintsRowMods.Com", "Saints Row Mods" )
		self.help_menu.AppendSeparator()
		self.help_menu.Append( 303, "&About", "About" )

		# Register the events
		wx.EVT_MENU( self, 100, self.load_fbx_file )
		#wx.EVT_MENU( self, 101, self.on_set_game_folder )
		#wx.EVT_MENU( self, 102, self.on_package_files )
		wx.EVT_MENU( self, 110, self.on_exit)
		wx.EVT_MENU( self, 201, self.toggle_remove )
		wx.EVT_MENU( self, 202, self.toggle_triangulate )
		wx.EVT_MENU( self, 203, self.toggle_3dsmax )
		wx.EVT_MENU( self, 204, self.toggle_Maya )
		wx.EVT_MENU( self, 300, self.open_url )
		wx.EVT_MENU( self, 301, self.open_url )
		wx.EVT_MENU( self, 302, self.open_url )
		wx.EVT_MENU( self, 304, self.open_url )
		wx.EVT_MENU( self, 303, self.about )

		# Create MenuBar and add Menu Items
		menuBar = wx.MenuBar()
		menuBar.Append( self.menu, "&File")
		menuBar.Append( self.settings_menu, "&Settings" )
		menuBar.Append( self.help_menu, "&Help" )

		self.SetMenuBar(menuBar)

		# when running as a python file dirname gets the parent directory,
		# when running as an exe, dirname is the local directory of library.zip ( strange )
		shaders_file = os.path.join( os.path.dirname( sys.path[0] ), 'sr_shaders.xml' )
		if not os.path.lexists( shaders_file ):
			shaders_file = os.path.join( sys.path[0], 'sr_shaders.xml' )

		if os.path.lexists( shaders_file ):
			self.shader_names, self.material_elements = get_shaders_from_xml( xml_file = shaders_file )
		else:
			wx.MessageBox( 'Make sure the "sr_shaders.xml" file is in the same directory as the FBX_Converter.exe', style = wx.OK, caption = 'Volition FBX Converter'  )

		self.table_grid = Table_Grid( self, self.shader_names )
		#self.table_grid.SetDefaultCellBackgroundColour((210,184,134))

		# SR LOGO
		image_file = 'saints_row_mods_logo.png'
		png = wx.Image(image_file, wx.BITMAP_TYPE_ANY).ConvertToBitmap()
		size = png.GetWidth(), png.GetHeight()
		self.bmp = wx.StaticBitmap(parent=self, bitmap=png)

		# FBX Box
		fbx_box = wx.StaticBox( self, 0, ' FBX ' )
		#bg_color = fbx_box.GetBackgroundColour()
		#fbx_box.SetForegroundColour((210,184,134))
		fbx_sizer = wx.StaticBoxSizer( fbx_box, wx.VERTICAL )
		#fbx_sizer = wx.BoxSizer( wx.VERTICAL )
		fbx_hsizer = wx.BoxSizer( wx.HORIZONTAL )
		logo_sizer = wx.BoxSizer( wx.HORIZONTAL )
		logo_sizer.AddSpacer( 15 )
		logo_sizer.Add( self.bmp, 0 )

		self.fbx_button = wx.Button( self, 3,'Import ', size = ( 50, 20 ) )
		#self.fbx_button.SetForegroundColour((210,184,134))
		self.fbx_button.Bind( wx.EVT_BUTTON, self.load_fbx_file )
		self.fbx_text = wx.TextCtrl( self, -1, "", size = ( 310, 21 ), style=wx.TE_READONLY  )
		self.fbx_text.SetBackgroundColour((210,184,134))
		self.Bind( wx.EVT_DROP_FILES, self.load_fbx_file, self.fbx_text )
		fbx_hsizer.AddSpacer( 5 )
		fbx_hsizer.Add( self.fbx_button, 0 )
		fbx_hsizer.AddSpacer( 5 )
		fbx_hsizer.Add( self.fbx_text, 0 )
		fbx_hsizer.AddSpacer( 5 )
		#fb_text = Label_Ctrl( self, text_string = "FBX", boxSize=( 390, 20), onTop = True)
		#fbx_sizer.Add( fb_text, 0, wx.TOP| wx.LEFT )
		fbx_sizer.AddSpacer( 1 )
		#fbx_sizer.Add( fbx_logo_sizer, 0, wx.ALIGN_CENTER, border = 0 )
		#fbx_sizer.AddSpacer( 5 )
		fbx_sizer.Add( fbx_hsizer, 0, wx.ALIGN_CENTER, border = 0 )
		fbx_sizer.AddSpacer( 5 )

		# Mesh Box
		mesh_box = wx.StaticBox( self, 1, ' MESH ' )
		#mesh_box.SetForegroundColour((210,184,134))
		mb_sizer = wx.StaticBoxSizer( mesh_box, wx.HORIZONTAL )
		mb_vSizer = wx.BoxSizer( wx.VERTICAL )

		temp_list = [ ]
		self.mesh_list = wx.ComboBox( self, 200, '', (90,50), (160,-1), temp_list, wx.CB_DROPDOWN )
		self.mesh_list.SetEditable( False )
		self.mesh_list.SetBackgroundColour((210,184,134))
		self.Bind( wx.EVT_COMBOBOX, self.on_select_mesh, self.mesh_list )

		#mat_text = Label_Ctrl( self, text_string = "Mesh", boxSize=( 390, 20), onTop = True)
		#mb_vSizer.Add( mat_text, 0, wx.TOP|wx.LEFT )
		mb_vSizer.AddSpacer( 6 )
		mesh_hSizer = wx.BoxSizer( wx.HORIZONTAL )
		mesh_hSizer.AddSpacer( 10 )
		mesh_hSizer.Add( self.mesh_list, 0, wx.LEFT| wx.TOP )
		mb_vSizer.Add( mesh_hSizer, 0, wx.TOP )
		mb_vSizer.AddSpacer( 10 )
		grid_hsizer = wx.BoxSizer( wx.HORIZONTAL )
		grid_hsizer.AddSpacer( 10 )
		grid_hsizer.Add( self.table_grid, 0, wx.TOP| wx.LEFT )
		grid_hsizer.AddSpacer( 7 )
		mb_vSizer.Add( grid_hsizer, 0, wx.TOP )
		mb_vSizer.AddSpacer( 8 )
		mb_sizer.Add( mb_vSizer, 0, wx.ALIGN_CENTER )

		# Mesh Info Box
		box = wx.StaticBox( self, 1, 'Mesh Info:')
		bsizer = wx.StaticBoxSizer( box, wx.VERTICAL )

		self.text_fill_count = wx.StaticText(self, -1, '                                                  ')
		self.text_triangle_count = wx.StaticText(self, -1, "  Triangles: ")
		self.text_vertex_count = wx.StaticText(self, -1,   "  Vertices: ")
		self.text_uv_count = wx.StaticText(self, -1, "  UVs: ")
		self.text_material_count = wx.StaticText(self, -1, "  Materials: ")
		self.text_bone_count = wx.StaticText(self, -1, "  Bones: ")
		self.text_collider_count = wx.StaticText(self, -1, "  Colliders: ")
		self.text_tag_count = wx.StaticText(self, -1, "  Tags: ")
		bsizer.Add( self.text_fill_count, 0, wx.TOP|wx.LEFT, 0)
		bsizer.AddSpacer( 5 )
		bsizer.Add( self.text_triangle_count, 0, wx.TOP|wx.LEFT, 0)
		bsizer.AddSpacer( 5 )
		bsizer.Add( self.text_vertex_count, 0, wx.TOP|wx.LEFT, 0)
		bsizer.AddSpacer( 5 )
		bsizer.Add( self.text_uv_count, 0, wx.TOP|wx.LEFT, 0)
		bsizer.AddSpacer( 5 )
		bsizer.Add( self.text_material_count, 0, wx.TOP|wx.LEFT, 0)
		bsizer.AddSpacer( 5 )
		bsizer.Add( self.text_bone_count, 0, wx.TOP|wx.LEFT, 0)
		bsizer.AddSpacer( 5 )
		bsizer.Add( self.text_collider_count, 0, wx.TOP|wx.LEFT, 0)
		bsizer.AddSpacer( 5 )
		bsizer.Add( self.text_tag_count, 0, wx.TOP|wx.LEFT, 0)
		bsizer.AddSpacer( 10 )

		# Export Box
		export_box = wx.StaticBox( self, 0, ' CONVERT ' )
		#export_box.SetForegroundColour((210,184,134))
		#export_box.SetBackgroundColour((210,184,134))
		export_sizer = wx.StaticBoxSizer( export_box, wx.VERTICAL )
		export_hsizer1 = wx.BoxSizer( wx.HORIZONTAL )
		export_hsizer2 = wx.BoxSizer( wx.HORIZONTAL )
		export_hsizer3 = wx.BoxSizer( wx.HORIZONTAL )
		export_hsizer4 = wx.BoxSizer( wx.HORIZONTAL )
		export_hsizer5 = wx.BoxSizer( wx.HORIZONTAL )

		# Package Box
		package_box = wx.StaticBox( self, 0, 'PACKAGE' )
		package_sizer = wx.StaticBoxSizer( package_box, wx.VERTICAL )
		package_hsizer1 = wx.BoxSizer( wx.HORIZONTAL )
		package_hsizer2 = wx.BoxSizer( wx.HORIZONTAL )

		self.package_folder_button = wx.Button( self, 3, 'Folder', size = ( 50, 20), style = 2)
		self.package_text = wx.TextCtrl( self, -1, "...", size = ( 310, 21 ), style=wx.TE_READONLY  )
		self.package_text.SetBackgroundColour((210,184,134))
		self.package_folder_button.Bind( wx.EVT_BUTTON, self.on_set_game_folder )

		self.package_button = wx.Button( self, 3,'Package ', size = ( 200, 22 ) )
		#self.button_export.SetBackgroundColour((210,184,134))
		self.package_button.Bind( wx.EVT_BUTTON, self.on_package_files )
		package_hsizer2.AddSpacer( 5 )
		package_hsizer2.Add( self.package_button, 0 )
		package_hsizer2.AddSpacer( 5 )

		package_hsizer1.AddSpacer( 5 )
		package_hsizer1.Add( self.package_folder_button, 0, wx.ALIGN_CENTER )
		package_hsizer1.AddSpacer( 5 )
		package_hsizer1.Add( self.package_text, 0 )
		package_hsizer1.AddSpacer( 5 )

		self.rig_button = wx.ToggleButton( self, 3,'Rigx ', size = ( 50, 20 ), style=2 )
		#self.rig_button.SetForegroundColour((210,184,134))
		self.rig_text = wx.TextCtrl( self, -1, "*.rigx", size = ( 310, 21 ), ) # style=wx.TE_READONLY  )
		self.rig_text.SetBackgroundColour((210,184,134))
		self.rig_text.Bind( wx.EVT_TEXT, self.on_set_rig_text )
		export_hsizer1.AddSpacer( 5 )
		export_hsizer1.Add( self.rig_button, 0, wx.ALIGN_CENTER )
		export_hsizer1.AddSpacer( 5 )
		export_hsizer1.Add( self.rig_text, 0 )
		export_hsizer1.AddSpacer( 5 )

		self.cmesh_button = wx.ToggleButton( self, 3,'Cmeshx ', size = ( 50, 20 ), style=0 )
		self.cmesh_text = wx.TextCtrl( self, -1, "*.cmeshx", size = ( 310, 21 ), ) #style=wx.TE_READONLY  )
		self.cmesh_text.SetBackgroundColour((210,184,134))
		self.cmesh_text.Bind( wx.EVT_TEXT, self.on_set_mesh_text )

		export_hsizer2.AddSpacer( 5 )
		export_hsizer2.Add( self.cmesh_button, 0 )
		export_hsizer2.AddSpacer( 5 )
		export_hsizer2.Add( self.cmesh_text, 0 )
		export_hsizer2.AddSpacer( 5 )

		self.matlib_button = wx.ToggleButton( self, 3,'Matlibx ', size = ( 50, 20 ), style=1 )
		self.matlib_text = wx.TextCtrl( self, -1, "*.matlibx", size = ( 310, 21 ), ) # style=wx.TE_READONLY  )
		self.matlib_text.SetBackgroundColour((210,184,134))
		self.matlib_text.Bind( wx.EVT_TEXT, self.on_set_mat_text )
		export_hsizer3.AddSpacer( 5 )
		export_hsizer3.Add( self.matlib_button, 0 )
		export_hsizer3.AddSpacer( 5 )
		export_hsizer3.Add( self.matlib_text, 0 )
		export_hsizer3.AddSpacer( 5 )

		self.morph_button = wx.ToggleButton( self, 3,'Morphx ', size = ( 50, 20 ), style=1 )
		self.morph_text = wx.TextCtrl( self, -1, "*.morphx", size = ( 310, 21 ), ) # style=wx.TE_READONLY  )
		self.morph_text.SetBackgroundColour((210,184,134))
		self.morph_text.Bind( wx.EVT_TEXT, self.on_set_mat_text )
		export_hsizer4.AddSpacer( 5 )
		export_hsizer4.Add( self.morph_button, 0 )
		export_hsizer4.AddSpacer( 5 )
		export_hsizer4.Add( self.morph_text, 0 )
		export_hsizer4.AddSpacer( 5 )
		self.button_export = wx.Button( self, 3,'Convert ', size = ( 200, 22 ) )
		#self.button_export.SetBackgroundColour((210,184,134))
		self.button_export.Bind( wx.EVT_BUTTON, self.convert_files )
		export_hsizer5.AddSpacer( 5 )
		export_hsizer5.Add( self.button_export, 0 )
		export_hsizer5.AddSpacer( 5 )

		#mat_text = Label_Ctrl( self, text_string = "Convert", boxSize=( 390, 20), onTop = True)
		#export_sizer.Add( mat_text, 0, wx.TOP )
		export_sizer.AddSpacer( 6 )
		export_sizer.Add( export_hsizer1, 0 )
		export_sizer.AddSpacer( 5 )
		export_sizer.Add( export_hsizer2, 0 )
		export_sizer.AddSpacer( 5 )
		export_sizer.Add( export_hsizer3, 0 )
		export_sizer.AddSpacer( 5 )
		export_sizer.Add( export_hsizer4, 0 )
		export_sizer.AddSpacer( 15 )
		export_sizer.Add( export_hsizer5, 0, wx.ALIGN_CENTER_HORIZONTAL )
		export_sizer.AddSpacer( 5 )

		package_sizer.AddSpacer( 6 )
		package_sizer.Add( package_hsizer1, 0 )
		package_sizer.AddSpacer( 15 )
		package_sizer.Add( package_hsizer2, 0, wx.ALIGN_CENTER_HORIZONTAL )
		package_sizer.AddSpacer( 5 )

		# Setup Layout
		self.mSizer = wx.BoxSizer(wx.VERTICAL)
		hSizer = wx.BoxSizer(wx.HORIZONTAL)
		vSizer = wx.BoxSizer(wx.VERTICAL)
		vSizer.AddSpacer( 7 )
		vSizerB = wx.BoxSizer(wx.VERTICAL)
		vSizerB.AddSpacer( 7 )
		vSizerB.Add( bsizer )
		sizer = wx.BoxSizer( wx.VERTICAL )
		sizer.AddSpacer( 2 )
		sizer.Add( logo_sizer, 0, wx.TOP )
		sizer.Add( fbx_sizer, 0, wx.BOTTOM )
		sizer.AddSpacer( 7 )
		sizer.Add( mb_sizer, 0, wx.TOP )
		sizer.AddSpacer( 7 )
		sizer.Add( export_sizer, 0, wx.TOP )
		sizer.AddSpacer( 7 )
		sizer.Add( package_sizer, 0, wx.TOP )
		sizer.AddSpacer( 15 )
		vSizer.Add( sizer, 0, wx.ALIGN_LEFT )
		hSizer.AddSpacer( 15 )
		hSizer.Add( vSizer, 0, wx.ALIGN_LEFT )
		hSizer.AddSpacer( 30 )
		hSizer.Add( vSizerB,0, wx.ALIGN_TOP )
		self.mSizer.Add( hSizer,0, wx.ALIGN_TOP )
		self.mSizer.AddSpacer( 20 )

		self.SetSizer( self.mSizer )

		# update settings
		self.load_settings( )

		self.update_ui( )


	def open_url( self, event, url = None ):
		"""
		Open a webpage

		*Arguments:*
			* ``event`` wx menu event

		*Keyword Arguments:*
			* ``None``

		*Author:*
			* Randall Hess, randall.hess@volition-inc.com, 7/8/2014 1:15:18 PM
		"""

		if not event.GetId() == 304:
			webbrowser.open('http://www.saintsrowmods.com')
		else:
			webbrowser.open('http://www.saintsrowmods.com/search')


	def about( self, event ):
		"""
		MessageBox that shows the about information

		*Arguments:*
			* ``Event`` menu event

		*Keyword Arguments:*
			* ``None``

		*Author:*
			* Randall Hess, randall.hess@volition-inc.com, 7/8/2014 1:20:49 PM
		"""
		version = 'Version: {0}'.format( self.version )
		message = 'Saints Row FBX Converter\nAuthor: Randall Hess\n' + version + \
		'\n\nDeveloped for the Saints Row modding community to convert FBX  \nmodels to the format needed for Saints Row IV and Saints Row: The Third.               ' + \
		'\n\nDeep Silver Volition:\nMike Watson, Mike Wilson, Mark Allender, John Lytle, David Payne,\nSeth Hawk, Dan Fike, Mike Flavin, Rob Rypka, Jeff Thompson,\nand Kate Marlin Nelson' + \
		'\n\nSpecial Thanks:\nThomas Rausch( donhonk ), Thomas Jepp\n\n'
		wx.MessageBox( message , style = wx.OK, caption = 'Saints Row FBX Converter' )


	def save_settings( self, ):
		"""
		Save converter settings

		*Arguments:*
			* ``None``

		*Keyword Arguments:*
			* ``None``

		*Returns:*
			* ``Value`` If any, enter a description for the return value here.

		*Author:*
			* Randall Hess, randall.hess@volition-inc.com, 7/7/2014 2:38:24 PM
		"""
		# update the config file
		config = { 'last_dir' : self.last_dir, 'remove_temp' : self.remove_temp_files, 'do_triangulate' : self.do_triangulate, 'game_folder' : self.game_folder, 'do_3dsmax' : self.do_3dsmax, 'do_Maya' : self.do_Maya }
		json.dump( config, open( self.config_file, 'w' ) )


	def load_settings( self, ):
		"""
		Load the converter settings
		Recent file locations and suck

		*Arguments:*
			* ``None``

		*Keyword Arguments:*
			* ``Argument`` Enter a description for the keyword argument here.

		*Returns:*
			* ``Value`` If any, enter a description for the return value here.

		*Examples:* ::

			Enter code examples here. (optional field)

		*Todo:*
			* Enter thing to do. (optional field)

		*Author:*
			* Randall Hess,   12/29/2013 1:50:16 AM
		"""
		self.config_file = os.path.join( WORKING_DIR, self.config_file )
		if os.path.lexists( self.config_file ):
			load_dict = json.load(open(self.config_file) )
			if load_dict:
				try:
					last_dir = load_dict[ 'last_dir' ]
					if not last_dir is None:
						self.last_dir = last_dir
				except KeyError:
					pass
				try:
					remove_temp = load_dict[ 'remove_temp' ]
					if not remove_temp is None:
						self.remove_temp_files = remove_temp
				except KeyError:
					pass
				try:
					do_triangulate = load_dict[ 'do_triangulate' ]
					if not do_triangulate is None:
						self.do_triangulate = do_triangulate
				except KeyError:
					pass
				try:
					do_Maya = load_dict[ 'do_Maya' ]
					if not do_Maya is None:
						self.do_Maya = do_Maya
				except KeyError:
					pass
				try:
					do_3dsmax = load_dict[ 'do_3dsmax' ]
					if not do_3dsmax is None:
						self.do_3dsmax = do_3dsmax
				except KeyError:
					pass
				try:
					game_folder = load_dict[ 'game_folder' ]
					if not do_triangulate is None:
						self.game_folder = game_folder
				except KeyError:
					pass


	def on_set_game_folder( self, event ):

		# pick the fbx file
		start_dir = ''
		game_folder = None
		open_dialog = wx.DirDialog( self, message = 'Pick your game folder, Common\\SaintsRowIV', defaultPath = WORKING_DIR )
		if open_dialog.ShowModal() == wx.ID_OK:
			game_folder = open_dialog.GetPath( )
		open_dialog.Destroy()

		if game_folder:
			self.game_folder = game_folder
			self.save_settings( )
			self.update_ui()


	def on_package_files( self, event ):
		if self.game_folder:
			if self.fbx_file:
				converted_folder = os.path.join( os.path.dirname( self.fbx_file ), 'output' )
				if os.path.lexists( converted_folder ):
					do_package = package_files( converted_folder, self.game_folder )
					if do_package:
						wx.MessageBox( 'Packaging files is complete', style = wx.OK, caption = 'Volition FBX Converter' )
					else:
						wx.MessageBox( 'FAILED Packaging files!\Check the output window for errors.', style = wx.OK, caption = 'Volition FBX Converter' )
				else:
					wx.MessageBox( 'Cant package files without an output folder', style = wx.OK, caption = 'Volition FBX Converter' )
			else:
				wx.MessageBox( 'No fbx file has been loaded!', style = wx.OK, caption = 'Volition FBX Converter' )
		else:
			wx.MessageBox( 'No game folder has been set through the file menu!', style = wx.OK, caption = 'Volition FBX Converter' )


	def convert_files( self, event, do_notify = True ):
		"""
		Export the selected files with the FBX data

		*Arguments:*
			* ``event`` wx.Event id

		*Keyword Arguments:*
			* ``Argument`` Enter a description for the keyword argument here.

		*Returns:*
			* ``Value`` If any, enter a description for the return value here.

		*Examples:* ::

			Enter code examples here. (optional field)

		*Todo:*
			* Enter thing to do. (optional field)

		*Author:*
			* Randall Hess,   12/29/2013 1:50:16 AM
		"""

		# get and set the manually assigned shaders
		if self.selected_mesh is None:
			wx.MessageBox( 'A mesh has not been selected to convert!' + '\n\nAborting Conversion' , style = wx.OK, caption = 'Volition FBX Converter' )
			return False

		for index in range( len( self.materials[ self.selected_mesh ] ) ):
			shader_value = self.table_grid.GetCellValue( index, 2 )
			if shader_value:
				self.materials[ self.selected_mesh ][ index ].shader = shader_value
				self.materials[ self.selected_mesh ][ index ].xml_element = self.material_elements[ shader_value ]
				if DEBUG_OUTPUT:
					print 'Material: {0} Shader: {1} XML_Element: {2}'.format( index, shader_value, self.material_elements[ shader_value ] )
			else:
				wx.MessageBox( 'Assign a shader to Material ' + str( index ) + '\nMaterial: ' + self.materials[ self.selected_mesh ][ index ].name + '\n\nAborting Conversion' , style = wx.OK, caption = 'Volition FBX Converter' )
				return False

		did_crunch = False
		did_convert = False
		write_rigx_file = False
		write_cmeshx_file = False
		write_matlibx_file = False

		# check to see if this is a static mesh
		static_mesh = False
		mesh_has_bones = self.bone_weights[ self.selected_mesh ]
		if not mesh_has_bones:
			static_mesh = True

		# get all the textures assigned and large
		all_textures = [ ]
		for i in self.textures[ self.selected_mesh ]:
			all_textures.append( i )

		# get high res textures
		small_large_textures = { }
		for texture in self.textures[ self.selected_mesh ]:
			base_name = os.path.basename( texture ).lower( )
			high_name = base_name.replace( '_sm_', '_lg_' )
			high_file = os.path.join( os.path.dirname( texture ), high_name )
			if os.path.lexists( high_file ):
				all_textures.append( high_file )
				small_large_textures[ texture ] = high_file

		global SMALL_LARGE_TEXTURES
		SMALL_LARGE_TEXTURES = small_large_textures

		# write the rigx
		if self.rig_button.GetValue( ):
			if not static_mesh:
				if DEBUG_OUTPUT:
					print("\n\n------------\nWrite Rigx\n------------\n")
				write_rigx_file = write_rigx( self.rigx_files[ self.selected_mesh ], self.bone_orders[ self.selected_mesh ], self.tags )
				if write_rigx_file:
					did_convert = True
					print 'Rigx file was written: {0}'.format( self.rigx_files[ self.selected_mesh ] )
					rig_rule = write_crunch_rule( self.rigx_files[ self.selected_mesh ], '.rigx' )
					did_crunch = crunch_rule( rig_rule )
					if did_crunch:
						print ' Crunched file: {0}'.format( rig_rule )
					else:
						print ' Failed to crunch file: {0}'.format( rig_rule )


			else:
				wx.MessageBox( 'This is a static mesh: ' + self.mesh_names[ self.selected_mesh ] + '\nNot exporting a rig file.\n\nConversion Warning' , style = wx.OK, caption = 'Volition FBX Converter' )

		# write the cmesh or smeshx
		ordered_verts = [ ]
		if self.cmesh_button.GetValue( ):
			if not static_mesh:
				try:
					write_cmeshx_file, ordered_verts = write_cmeshx( self.cmeshx_files[ self.selected_mesh ], self.meshes[ self.selected_mesh ], self.mesh_names[ self.selected_mesh ], self.mesh_data[ self.selected_mesh ], self.vertices[ self.selected_mesh ], self.bone_orders[ self.selected_mesh ], self.tags, self.materials[ self.selected_mesh ], self.bone_weights[ self.selected_mesh ], static_mesh = False )
				except IOError:
					wx.MessageBox( 'Cannot write to the file at this time: ' + sself.cmeshx_files[ self.selected_mesh ], style = wx.OK, caption = 'Volition FBX Converter' )

				if write_cmeshx_file:
					print 'Cmeshx file was written: {0}'.format( self.cmeshx_files[ self.selected_mesh ] )
			else:
				# write out a smeshx instead
				write_cmeshx_file = write_cmeshx( self.smeshx_files[ self.selected_mesh ], self.meshes[ self.selected_mesh ], self.mesh_names[ self.selected_mesh ], self.mesh_data[ self.selected_mesh ], self.vertices[ self.selected_mesh ], self.bone_orders[ self.selected_mesh ], self.tags, self.materials[ self.selected_mesh ], self.bone_weights[ self.selected_mesh ], static_mesh = True )
				if write_cmeshx_file:
					print 'Smeshx file was written: {0}'.format( self.smeshx_files[ self.selected_mesh ] )

			if write_cmeshx_file:
				did_convert = True

				if not static_mesh:
					mesh_rule = write_crunch_rule( self.cmeshx_files[ self.selected_mesh ], '.cmeshx' )
					did_crunch = crunch_rule( mesh_rule )
					if did_crunch:
						print ' Crunched file: {0}'.format( mesh_rule )
					else:
						print ' Failed to crunch file: {0}'.format( mesh_rule )
				else:
					mesh_rule = write_crunch_rule( self.smeshx_files[ self.selected_mesh ], '.smeshx' )
					did_crunch = crunch_rule( mesh_rule )
					if did_crunch:
						print ' Crunched file: {0}'.format( mesh_rule )
					else:
						print ' Failed to crunch file: {0}'.format( mesh_rule )

		# write and crunch the matlibx
		if self.matlib_button.GetValue( ):
			#if not static_mesh:
			write_matlibx_file = write_matlibx( self.matlibx_files[ self.selected_mesh ], self.materials[ self.selected_mesh ] )
			if write_matlibx_file:
				did_convert = True
				print 'Matlibx file was written: {0}'.format( self.matlibx_files[ self.selected_mesh ] )
				mat_rule = write_crunch_rule( self.matlibx_files[ self.selected_mesh ], '.matlibx' )
				did_crunch = crunch_rule( mat_rule )
				if did_crunch:
					print ' Crunched file: {0}'.format( mat_rule )
				else:
					print ' Failed to crunch file: {0}'.format( mat_rule )

		# write and crunch the morphx
		if ordered_verts:
			if self.morph_button.GetValue( ):
				if not static_mesh:
					if self.blendshapes[ self.selected_mesh ]:
						write_morphx_file = write_morphx( self.morphx_files[ self.selected_mesh ], self.cmeshx_files[ self.selected_mesh ], self.meshes[ self.selected_mesh ], self.mesh_names[ self.selected_mesh ], self.vertices[ self.selected_mesh ], self.blendshapes[ self.selected_mesh ], self.mesh_data[ self.selected_mesh ], ordered_verts )
						if write_morphx_file:
							did_convert = True
							print 'Morphx file was written: {0}'.format( self.morphx_files[ self.selected_mesh ] )
							morph_rule = write_crunch_rule( self.morphx_files[ self.selected_mesh ], '.morphx' )
							did_crunch = crunch_rule( morph_rule )
							if did_crunch:
								print ' Crunched file: {0}'.format( morph_rule )
							else:
								print ' Failed to crunch file: {0}'.format( morph_rule )

		# write out the peg rule
		timer_val = 2.25
		total_time = 0.0
		if write_cmeshx_file or write_matlibx_file:

			# write a rule for each texture file
			for texture in all_textures:

				if static_mesh:
					texture_rule = write_crunch_rule( self.smeshx_files[ self.selected_mesh ], '.texture', textures = texture )
					did_crunch = crunch_rule( texture_rule )
					if did_crunch:
						print ' Crunched file: {0}'.format( texture_rule )
					else:
						print ' Failed to crunch file: {0}'.format( texture_rule )
				else:
					texture_rule = write_crunch_rule( self.cmeshx_files[ self.selected_mesh ], '.texture', textures = texture )
					did_crunch = crunch_rule( texture_rule )
					if did_crunch:
						print ' Crunched file: {0}'.format( texture_rule )
					else:
						print ' Failed to crunch file: {0}'.format( texture_rule )

				# wait for the textures to crunch this is not very reliable..
				time.sleep( timer_val )
				total_time += timer_val

			# write out the mesh peg files
			if static_mesh:
				peg_rule = write_crunch_rule( self.smeshx_files[ self.selected_mesh ], '.peg', textures = self.textures[ self.selected_mesh ] )
				did_crunch = crunch_rule( peg_rule )
				if did_crunch:
					print ' Crunched file: {0}'.format( peg_rule )
				else:
					print ' Failed to crunch file: {0}'.format( peg_rule )
			else:
				peg_rule = write_crunch_rule( self.cmeshx_files[ self.selected_mesh ], '.peg', textures = self.textures[ self.selected_mesh ] )
				did_crunch = crunch_rule( peg_rule )
				if did_crunch:
					print ' Crunched file: {0}'.format( peg_rule )
				else:
					print ' Failed to crunch file: {0}'.format( peg_rule )

			# write out the matlib peg file
			if write_matlibx_file:

				# pass through lg textures if found
				use_textures = [ ]
				for texture in self.textures[ self.selected_mesh ]:
					this_texture = texture
					for key, val in small_large_textures.iteritems( ):
						if key == texture:
							this_texture = val
							break
					use_textures.append( this_texture )

				peg_rule = write_crunch_rule( self.matlibx_files[ self.selected_mesh ], '.peg', textures = use_textures )
				did_crunch = crunch_rule( peg_rule )
				if did_crunch:
					print ' Crunched file: {0}'.format( peg_rule )
				else:
					print ' Failed to crunch file: {0}'.format( peg_rule )

		self.SetSizer( self.mSizer )
		self.SetFocus( )

		if do_notify:
			if not did_convert:
				wx.MessageBox( 'Nothing was selected to convert!', style = wx.OK, caption = 'Volition FBX Converter' )
			else:
				#print '\n\nRunning twice just to make sure textures were crunched before pegs were assembled:\n'
				#self.convert_files( wx.EVT_BUTTON, do_notify = False )
				if self.remove_temp_files:
					time.sleep( total_time )

					# delete temp crunched texture files
					intermediate_names = [ '.cmeshx', '.rigx', '.smeshx', '.matlibx' ]
					local_dir = os.path.dirname( self.fbx_file )
					if os.path.lexists( local_dir ):
						files = os.listdir( local_dir )
						if files:
							for afile in files:
								end_pc = afile.endswith( '_pc' )
								is_intermediate = False
								for ext in intermediate_names:
									if afile.endswith( ext ):
										is_intermediate = True
										break
								if end_pc or is_intermediate:
									print '\tRemoving temp file: {0}'.format( afile )
									os.remove( os.path.join( local_dir, afile ) )

						output_dir = os.path.join( local_dir, 'output' )
						if os.path.lexists( output_dir ):
							files = os.listdir( output_dir )
							if files:
								for afile in files:
									if afile.endswith( '.log' ):
										print '\tRemoving temp file: {0}'.format( afile )
										os.remove( os.path.join( output_dir, afile ) )

				# move intermediate files
				wx.MessageBox( 'Conversion completed!', style = wx.OK, caption = 'Volition FBX Converter' )

		return True


	def reset_variables( self ):
		"""
		When importing or refreshing an Fbx file reset all the variables

		*Arguments:*
			* ``None``

		*Keyword Arguments:*
			* ``None``

		*Author:*
			* Randall Hess,   12/29/2013 1:44:35 PM
		"""

		self.fbx_file = None
		self.coordinate_system_transform = None

		self.colliders = [ ]
		self.bones = [ ]
		self.bone_orders = [ ]
		self.bone_weights = [ ]
		self.tags = [ ]
		self.vertices = [ ]
		self.meshes = [ ]
		self.mesh_names = [ ]
		self.mesh_data = [ ]
		self.materials = [ ]
		self.material_names = [ ]
		self.textures = [ ]
		self.selected_mesh = None
		self.selected_material = None
		self.rigx_file = None
		self.rigx_files = [ ]
		self.cmeshx_file = None
		self.cmeshx_files = [ ]
		self.smeshx_file = None
		self.smeshx_files = [ ]
		self.matlibx_file = None
		self.matlibx_files = [ ]
		self.node_index = 0
		self.nodes = { }
		self.blendshapes = [ ]
		self.morphx_file = None
		self.morphx_files = [ ]

		self.update_ui( )


	def toggle_remove( self, event ):
		"""
		Toggle the removal of temporary files

		*Arguments:*
			* ``wx.Event`` wx event

		*Keyword Arguments:*
			* ``None``

		*Returns:*
			* ``None``

		*Author:*
			* Randall Hess, randall.hess@volition-inc.com, 7/4/2014 1:36:55 AM
		"""

		self.remove_temp_files = not self.remove_temp_files
		self.settings_menu.Check( 201, self.remove_temp_files )
		self.save_settings( )


	def toggle_triangulate( self, event ):
		"""
		Toggle the triangulation of meshes by the converter

		*Arguments:*
			* ``wx.Event`` wx event

		*Keyword Arguments:*
			* ``None``

		*Returns:*
			* ``None``

		*Author:*
			* Randall Hess, randall.hess@volition-inc.com, 7/4/2014 1:36:55 AM
		"""

		self.do_triangulate = not self.do_triangulate
		self.settings_menu.Check( 202, self.do_triangulate )
		self.save_settings( )

	def toggle_3dsmax( self, event ):
		"""
		Toggle the conversion to 3dsmax

		*Arguments:*
			* ``wx.Event`` wx event

		*Keyword Arguments:*
			* ``None``

		*Returns:*
			* ``None``

		*Author:*
			* Randall Hess, randall.hess@volition-inc.com, 7/4/2014 1:36:55 AM
		"""

		self.do_3dsmax = not self.do_3dsmax
		if self.do_3dsmax:
			self.do_Maya = False
		self.settings_menu.Check( 203, self.do_3dsmax )
		self.settings_menu.Check( 204, self.do_Maya )
		self.save_settings( )


	def toggle_Maya( self, event ):
		"""
		Toggle the conversion to Maya

		*Arguments:*
			* ``wx.Event`` wx event

		*Keyword Arguments:*
			* ``None``

		*Returns:*
			* ``None``

		*Author:*
			* Randall Hess, randall.hess@volition-inc.com, 7/4/2014 1:36:55 AM
		"""

		self.do_Maya = not self.do_Maya
		if self.do_Maya:
			self.do_3dsmax = False
		self.settings_menu.Check( 203, self.do_3dsmax )
		self.settings_menu.Check( 204, self.do_Maya )
		self.save_settings( )


	def load_fbx_file( self, event ):
		"""
		Import and Load the fbx file
		return the data needed to write out volition intermediate files
		*.rigx
		*.cmeshx
		*.matlibx

		*Arguments:*
			* ``Argument`` Enter a description for the argument here.

		*Keyword Arguments:*
			* ``Argument`` Enter a description for the keyword argument here.

		*Returns:*
			* ``fbx file`` actual fbx file on disk

		*Author:*
			* Randall Hess,   12/28/2013 9:28:01 PM
		"""

		fbx_file = None
		print 'Working Directory: {0}'.format( WORKING_DIR )

		start_dir = ''
		if self.last_dir:
			if os.path.lexists( self.last_dir ):
				start_dir = self.last_dir

		# pick the fbx file
		open_dialog = wx.FileDialog( self, message = 'Choose a file', defaultDir = start_dir, defaultFile='', wildcard = 'Autodesk FBX (*.FBX)|*.fbx' )
		if open_dialog.ShowModal() == wx.ID_OK:
			fbx_file = open_dialog.GetPath( )
		open_dialog.Destroy()

		if fbx_file:

			# update the config file
			self.last_dir = os.path.dirname( fbx_file )
			self.save_settings( )

			self.SetStatusText( 'Importing FBX File ...' )
			self.reset_variables( )
			self.fbx_file = fbx_file

			progress_dlg = wx.lib.agw.pyprogress.PyProgress( None, -1, "Importing FBX File", "Processing the FBX file", agwStyle=wx.PD_APP_MODAL )

			# get the fbx file location and name
			file_dir = os.path.dirname( self.fbx_file )
			base_name = os.path.basename( self.fbx_file )
			base_no_ext = os.path.splitext( base_name )[ 0 ]

			# Load the fbx scene
			fbx_status, fbx_scene, lSdkManager = load_fbx_scene( fbx_file, self.do_3dsmax, self.do_Maya )
			if fbx_status:

				if DEBUG_OUTPUT:
					print("\n\n---------\nGet Scene Hierarchy\n---------\n")

				self.SetStatusText( 'Getting the FBX Hierarchy ...' )
				self.get_fbx_hierarchy( fbx_scene )

				if DEBUG_OUTPUT:
					print("\n\n------------\nGet Bone Hierarchy\n------------\n")

				# triangulate all meshes in the scene
				if self.do_triangulate:
					print 'Triangulating meshes'
					geo_converter = FbxCommon.FbxGeometryConverter( lSdkManager )
					if geo_converter:
						do_triangulate = geo_converter.Triangulate( fbx_scene, True, False )

				# Filter out any mesh objects that might be acting as bones
				# remove any of those "bones" from the mesh list
				for mesh in self.meshes:
					lmesh = mesh.GetNodeAttribute( )

					# get the vert/weight info
					self.SetStatusText( 'Getting Mesh Bone Weights: {0}'.format( mesh.GetName( ) ) )
					progress_dlg._msg.SetLabelText( 'Getting Bone Weights' )
					bone_weights, bones = get_boneweights( lmesh, [ ], self.bones, progress_dlg )
					#self.bone_weights.append( bone_weights )

					# determine if bones found in bone weights are in the self.meshes list
					# if they are in the self.meshes list, we need to remove them,
					# we also need to create_bones from these objects
					for bone_name, bone_node in bones.iteritems( ):
						if DEBUG_OUTPUT:
							print 'Mesh: {0} Bone Name: {1} Bone Node: {2}'.format( mesh.GetName(), bone_name, bone_node )
						if bone_node in self.meshes:
							self.meshes.pop( self.meshes.index( bone_node ) )
							# create the bone object
							self.create_bone( bone_node, fbx_scene )

				# Make sure every bone is index'ed properly
				progress_dlg._msg.SetLabelText( 'Updating bone attributes' )
				for bone in self.bones:
					if not bone.index:
						try:
							node_obj = self.nodes[ bone.node ]
							if node_obj:
								bone.index = node_obj.index
							bone.update_attributes( )
						except KeyError:
							# all the nodes should be found
							pass

				# if the indices on the bones were updated we need to loop back through and update parent references to those ids
				for bone in self.bones:
					bone.update_attributes( )

				# Get the mesh face data ( Verts, Normals, UV's )
				for mesh in self.meshes:

					# zero the position of static meshes
					lmesh = mesh.GetNodeAttribute( )
					if lmesh.GetDeformerCount() == 0:
						mesh_gbl_transform = mesh.EvaluateGlobalTransform()
						mesh_gbl_transform.SetT( FbxCommon.FbxVector4() )
						mesh_lcl_transform = mesh.EvaluateLocalTransform()
						mesh_lcl_transform.SetT( FbxCommon.FbxVector4() )

					self.SetStatusText( 'Getting Mesh Data: {0}'.format( mesh.GetName( ) ) )
					progress_dlg._msg.SetLabelText( 'Getting the Mesh Data...' )

					mesh_data, vertices = get_mesh_data( mesh, progress_dlg )
					if not mesh_data or not vertices:
						lSdkManager.Destroy()
						progress_dlg.Destroy( )
						wx.MessageBox( 'This mesh was not exported with Triangulate on.\n{0}\n\nExport the fbx file again with Triangulate checked on or toggle on Triangulate Mesh in the Settings!'.format( self.fbx_file ), style = wx.OK )
						return False

					num_polygon_verts = lmesh.GetPolygonVertexCount( )
					self.mesh_data.append( mesh_data )
					self.vertices.append( vertices )

					colliders = [ ] # TODO get colliders
					self.colliders.append( colliders )

					num_polygons = lmesh.GetPolygonCount( )

					# get the vert/weight info
					self.SetStatusText( 'Getting Mesh Bone Weights: {0}'.format( mesh.GetName( ) ) )
					progress_dlg._msg.SetLabelText( 'Getting Bone Weights..' )
					bone_weights, bones = get_boneweights( lmesh, vertices, self.bones, progress_dlg )

					# only add a mesh to the list if it has bones
					# we are only exporting character meshes at this time
					if bones:
						self.bone_weights.append( bone_weights )
					else:
						self.bone_weights.append( None )

					self.mesh_names.append( mesh.GetName() )
					self.SetStatusText( 'Get the bone order ...' )
					self.update_bone_attributes( self.bones, self.nodes )
					progress_dlg._msg.SetLabelText( 'Getting the Bone Order...' )
					bone_order = self.get_bone_order( progress_dlg )
					self.bone_orders.append( bone_order )

					# if there are bones its likely a skinned mesh
					# check for blendshapes
					blendshapes = get_blendshapes( mesh, vertices, progress_dlg)
					if len( blendshapes ) > 0:
						self.blendshapes.append( blendshapes )
					else:
						self.blendshapes.append( None )

				# update the file lists based on the mesh inputs
				for mesh in self.meshes:
					self.matlibx_files.append( None )
					self.cmeshx_files.append( None )
					self.rigx_files.append( None )
					self.smeshx_files.append( None )
					self.morphx_files.append( None )

				# get the materials
				for mesh in self.meshes:
					lmesh = mesh.GetNodeAttribute( )

					progress_dlg._msg.SetLabelText( 'Getting the materials...' )
					materials = get_fbx_materials( lmesh )
					mats = [ ]
					textures = [ ]
					mat_index = 0
					for material in materials:
						wx.Yield( )
						progress_dlg.UpdatePulse( )

						# setup the new material object
						new_mat = Material_Info( mat_index, material.GetName() )
						mat_index += 1

						# Get and Set the Material Texture Properties
						for texture_index in range( FbxCommon.FbxLayerElement.sTypeTextureCount() ):
							texture_property = material.FindProperty( FbxCommon.FbxLayerElement.sTextureChannelNames( texture_index ) )
							if DEBUG_OUTPUT:
								print 'Material: {0} Texture property: {1}'.format( material.GetName(), texture_property.GetName() )
							if texture_property.IsValid():
								texture_prop_name = texture_property.GetName()
								if DEBUG_OUTPUT:
									print 'Material: {0} Texture property: {1}'.format( material.GetName(), texture_prop_name )

								texture_filename = None
								num_textures = texture_property.GetSrcObjectCount( FbxCommon.FbxTexture.ClassId )
								for num in range( num_textures ):
									cur_texture = texture_property.GetSrcObject( FbxCommon.FbxTexture.ClassId, num )
									if cur_texture:
										texture_filename =cur_texture.GetFileName( )
										if DEBUG_OUTPUT:
											print '\t2) lTexture: {0} FileName: {1}'.format( cur_texture.GetName(), cur_texture.GetFileName( ) )

								# fill out the material property/ texture file references
								if texture_filename:
									if texture_prop_name == 'DiffuseColor':
										new_mat.diffuse_map = texture_filename
									elif texture_prop_name == 'SpecularColor':
										new_mat.specular_map = texture_filename
									elif texture_prop_name == 'NormalMap':
										new_mat.normal_map = texture_filename
									elif texture_prop_name == 'Bump':
										new_mat.normal_map = texture_filename
									elif texture_prop_name == 'AmbientColor':
										new_mat.sphere_map1 = texture_filename
									elif texture_prop_name == 'DisplacementColor':
										new_mat.sphere_map2 = texture_filename
									elif texture_prop_name == 'TransparentColor':
										new_mat.blend_map = texture_filename
									elif texture_prop_name == 'EmissiveColor':
										new_mat.glow_Mask_Map = texture_filename

									if not texture_filename in textures:
										textures.append( texture_filename )

						# add the new material info
						mats.append( new_mat )

					# update the materials list with the new infos
					self.materials.append( mats )
					self.textures.append( textures )

				self.SetStatusText( 'FBX File loaded: {0}'.format(  fbx_file.lower( ) ) )

				# Destroy all objects created by the FBX SDK.
				lSdkManager.Destroy()
				progress_dlg.Destroy( )

		wx.Yield( )
		self.SetFocus( )
		self.update_ui( )

		return True


	def update_bone_attributes( self, bones, nodes ):
		"""
		Make sure the attributes on the bones are updated if they didnt previously exist

		*Arguments:*
			* ``Argument`` Enter a description for the argument here.

		*Keyword Arguments:*
			* ``Argument`` Enter a description for the keyword argument here.

		*Returns:*
			* ``Value`` If any, enter a description for the return value here.

		*Examples:* ::

			Enter code examples here. (optional field)

		*Todo:*
			* Enter thing to do. (optional field)

		*Author:*
			* Randall Hess,  1/20/2014 2:34:07 PM
		"""

		for bone in bones:

			node_obj = None
			parent = None
			node_parent = None

			node_obj = nodes[ bone.node ]
			if node_obj:

				# set the index
				if not bone.index:
					if bone.index == 0:
						exit
					else:
						bone.index = node_obj.index
						bone.id = bone.index


	def create_tag( self, node, scene ):
		"""
		If the incoming node is a "tag", create a tag object for it

		*Arguments:*
			* ``node`` fbx node
			* ``scene`` fbx scene

		*Keyword Arguments:*
			* ``none``

		*Returns:*
			* ``none``

		*Examples:* ::

			Enter code examples here. (optional field)

		*Todo:*
			* Enter thing to do. (optional field)

		*Author:*
			* Randall Hess,   11/22/2013 8:58:52 AM
		"""

		node_is_tag = get_node_properties( node, property_name = 'p_tag_name' )
		if node_is_tag or node.GetName().startswith( 'tag_' ):
			tag = Node_Tag( node, scene )
			self.tags.append( tag )


	def create_mesh( self, node, scene ):
		"""
		If the incoming node is a "mesh", create a mesh object for it

		*Arguments:*
			* ``node`` fbx node
			* ``scene`` fbx scene

		*Keyword Arguments:*
			* ``none``

		*Returns:*
			* ``none``

		*Examples:* ::

			Enter code examples here. (optional field)

		*Todo:*
			* Enter thing to do. (optional field)

		*Author:*
			* Randall Hess,   11/22/2013 8:58:52 AM
		"""

		# make sure it isn't a mesh posing as a bone
		node_is_bone = get_node_properties( node, property_name = 'p_bone_name' )
		if node_is_bone or node.GetName().startswith( 'bone_' ):
			self.create_bone( node, scene )
		else:
			if not node.GetName().lower().startswith( 'collider_' ):
				self.meshes.append( node )


	def create_bone( self, node, scene ):
		"""
		If the incoming node is a "bone", create a bone object for it

		*Arguments:*
			* ``node`` fbx node
			* ``scene`` fbx scene

		*Keyword Arguments:*
			* ``none``

		*Returns:*
			* ``none``

		*Examples:* ::

			Enter code examples here. (optional field)

		*Todo:*
			* Enter thing to do. (optional field)

		*Author:*
			* Randall Hess,   11/22/2013 8:58:52 AM
		"""

		#node_is_bone = get_node_properties( node, property_name = 'p_bone_name' )
		node_is_bone = True
		if node_is_bone:
			bone = Node_Bone( node, scene )
			self.bones.append( bone )


	def get_node_content( self, node, scene ):
		"""
		Determine the type of the incoming node and create a specific object that we will use later

		*Arguments:*
			* ``node`` fbx node
			* ``scene`` fbx scene

		*Keyword Arguments:*
			* ``none``

		*Returns:*
			* ``Value`` If any, enter a description for the return value here.

		*Examples:* ::

			Enter code examples here. (optional field)

		*Todo:*
			* Enter thing to do. (optional field)

		*Author:*
			* Randall Hess,   11/22/2013 9:02:46 AM
		"""

		if node.GetNodeAttribute( ) == None:
			print("NULL Node Attribute\n")
		else:

			# Get the node type
			node_attribute_type = ( node.GetNodeAttribute( ).GetAttributeType( ) )
			if node_attribute_type == FbxCommon.FbxNodeAttribute.eSkeleton:
				self.create_bone( node, scene )

			elif node_attribute_type == FbxCommon.FbxNodeAttribute.eMesh:
				self.create_mesh( node, scene )

			elif node_attribute_type == FbxCommon.FbxNodeAttribute.eNull:
				self.create_tag( node, scene )

			else:
				print 'Node is not a type that we care about right now: {0}'.format( node.GetName( ) )
				pass


	def get_node_hierarchy( self, node, node_depth, scene ):
		"""
		Recursively get the heirarchy of objects from the FBX scene derived from the give root node, node

		*Arguments:*
			* ``node`` Current fbx scene root node
			* ``node_depth`` Depth of current node in the fbx scene
			* ``scene`` Fbx scene

		*Keyword Arguments:*
			* ``none``

		*Returns:*
			* ``Value`` If any, enter a description for the return value here.

		*Examples:* ::

			Enter code examples here. (optional field)

		*Todo:*
			* Enter thing to do. (optional field)

		*Author:*
			* Randall Hess,   11/22/2013 8:48:28 AM
		"""

		if DEBUG_OUTPUT:
			print 'Node: {0} NodeIndex: {1} Depth: {2}'.format( node.GetName(), self.node_index, node_depth )

		if node.GetParent( ):
			if DEBUG_OUTPUT:
				print '\tParent: {0}'.format( node.GetParent().GetName() )

		node_obj = Node_Info( node, self.node_index )
		self.nodes[ node ] = node_obj

		node_string = ""
		for i in range( node_depth ):
			node_string += "     "

		node_string += node.GetName( )
		if DEBUG_OUTPUT:
			print( node_string )
		self.get_node_content( node, scene )

		for i in range( node.GetChildCount( ) ):
			self.node_index += 1
			self.get_node_hierarchy( node.GetChild( i ), node_depth + 1, scene )



	def get_fbx_hierarchy( self, scene ):
		"""
		Get the heirarchy of objects from the FBX scene
		Starting with the scene root objects

		*Arguments:*
			* ``scene`` Fbx scene

		*Keyword Arguments:*
			* ``none``

		*Returns:*
			* ``none``

		*Examples:* ::

			Enter code examples here. (optional field)

		*Todo:*
			* Enter thing to do. (optional field)

		*Author:*
			* Randall Hess,   11/22/2013 8:46:57 AM
		"""
		scene_hierarchy = { }

		scene_root_node = scene.GetRootNode( )

		self.node_index = 0
		for i in range( scene_root_node.GetChildCount( ) ) :
			self.get_node_hierarchy( scene_root_node.GetChild( i ), 0, scene )
			self.node_index += 1


	def get_bone_order( self, progress_dlg ):
		"""
		With the given bones order them so they can be arranged and written out properly

		*Arguments:*
			* ``BONES`` Enter a description for the argument here.

		*Keyword Arguments:*
			* ``none``

		*Returns:*
			* ``bone_order`` Dict of Fbx bones and the associated order

		*Examples:* ::

			Enter code examples here. (optional field)

		*Todo:*
			* Enter thing to do. (optional field)

		*Author:*
			* Randall Hess,   11/19/2013 9:34:40 PM
		"""

		bone_order = { }

		# put the bones and index into a dict that we can sort
		if self.bones:
			for bone in self.bones:
				if DEBUG_BONE_OUTPUT:
					print 'Bone: {0} Order: {1}'.format( bone.name, bone.index )
				bone_order[ bone.index ] = bone

			if DEBUG_BONE_OUTPUT:
				print 'Sorted Bone Order Keys: {0}'.format( sorted( bone_order.keys( ) ) )

			order = 0
			for index in sorted( bone_order.keys( ) ):
				if DEBUG_BONE_OUTPUT:
					print ' Setting Bone: {0} Order: {1}'.format( bone_order[index].name, order )
				if order % 5 == 0:
					wx.Yield( )
					progress_dlg._msg.SetLabelText( 'Sorting bones: {0}'.format( order ) )
					progress_dlg.UpdatePulse( )
				bone_order[index].index = order
				bone_order[index].id = order
				order += 1

			# update Tags parent index from this new order
			for tag in self.tags:
				if DEBUG_BONE_OUTPUT:
					print 'Tag: {0}'.format( tag.name )
				for index in sorted( bone_order.keys( ) ):
					# if the tag parent is the current bone set the index
					if tag.parent == bone_order[ index ].node:
						if DEBUG_BONE_OUTPUT:
							print '  Found Parent: {0}'.format( bone_order[ index ].name )
						tag.parent_index = bone_order[ index ].index
						break

			# update Bones parent index from this new order
			for bone in self.bones:
				for index in sorted( bone_order.keys( ) ):
					# if the bone parent is the current bone set the index
					if bone.node.GetParent() == bone_order[ index ].node:
						if DEBUG_BONE_OUTPUT:
							print 'Bone:{0} ParentID:{1}'.format( bone.name, bone_order[index].id )
						bone.parent_id = bone_order[ index ].id
						bone.parent = bone_order[ index ].index
						break

			for bone in self.bones:
				if bone.parent is None:
					bone.parent = -1
					bone.parent_id = -1
					bone.parent_index = -1

		return bone_order


	def on_select_material( self, event ):
		"""
		Handle updating the UI when selecting a different material
		Set the material selection index

		*Arguments:*
			* ``event`` Id for the wx.Event

		*Keyword Arguments:*
			* ``None``

		*Returns:*
			* ``None``

		*Examples:* ::

			Enter code examples here. (optional field)

		*Todo:*
			* Enter thing to do. (optional field)

		*Author:*
			* Randall Hess,   12/28/2013 11:50:19 PM
		"""


		# Get the selection name
		selection = self.material_listbox.the_listbox.GetSelection()

		if selection > -1:
			selected_string = None
			try:
				selected_string = self.material_listbox.the_listbox.GetString( selection )
			except AssertionError:
				pass
			except IndexError:
				pass

			if selected_string:
				selected_string = str( selected_string.strip(  ) )
				self.selected_material = selection

		self.update_ui( )


	def on_set_rig_text( self, event ):
		"""
		Update the self.rigx_file value from text entered

		*Arguments:*
			* ``event`` wx.text entered event

		*Keyword Arguments:*
			* ``none``

		*Returns:*
			* ``none``

		*Author:*
			* Randall Hess, randall.hess@volition-inc.com, 4/29/2014 8:00:57 AM
		"""

		if self.selected_mesh > -1:
			text_value = self.rig_text.GetValue( )
			if not text_value.startswith( '*.' ):
				if self.bone_weights[ self.selected_mesh ]:
					self.rigx_files[ self.selected_mesh ] = text_value


	def on_set_mesh_text( self, event ):
		"""
		Update the self.cmeshx_file/self.smeshx_file value from text entered

		*Arguments:*
			* ``event`` wx.text entered event

		*Keyword Arguments:*
			* ``none``

		*Returns:*
			* ``none``

		*Author:*
			* Randall Hess, randall.hess@volition-inc.com, 4/29/2014 8:00:57 AM
		"""

		if self.selected_mesh > -1:
			text_value = self.cmesh_text.GetValue( )
			if not text_value.startswith( '*.' ):
				if self.bone_weights[ self.selected_mesh ]:
					self.cmeshx_files[ self.selected_mesh ] = text_value
				else:
					self.smeshx_files[ self.selected_mesh ] = text_value


	def on_set_mat_text( self, event ):
		"""
		Update the self.matlibx_file value from text entered

		*Arguments:*
			* ``event`` wx.text entered event

		*Keyword Arguments:*
			* ``none``

		*Returns:*
			* ``none``

		*Author:*
			* Randall Hess, randall.hess@volition-inc.com, 4/29/2014 8:00:57 AM
		"""
		if self.selected_mesh > -1:
			text_value = self.matlib_text.GetValue( )
			if not text_value.startswith( '*.' ):
				self.matlibx_files[ self.selected_mesh ] = text_value



	def on_select_mesh( self, event ):
		"""
		Handle updating the UI when selecting a different mesh
		Set the mesh selection index

		*Arguments:*
			* ``event`` Id for the wx.Event

		*Keyword Arguments:*
			* ``None``

		*Returns:*
			* ``None``

		*Examples:* ::

			Enter code examples here. (optional field)

		*Todo:*
			* Enter thing to do. (optional field)

		*Author:*
			* Randall Hess,   12/28/2013 11:50:19 PM
		"""

		# Get the selection name
		selection = self.mesh_list.GetSelection()

		if selection > -1:
			selected_string = None
			try:
				selected_string = self.mesh_list.GetString( selection )
			except AssertionError:
				pass
			except IndexError:
				pass

			if selected_string:
				selected_string = str( selected_string.strip(  ) )
				self.selected_mesh = selection
				self.mesh_selection = selection

		self.update_ui( )


	def update_ui( self ):
		"""
		Update the user inteface to reflect selected meshes and material info

		*Arguments:*
			* ``None``

		*Keyword Arguments:*
			* ``None``

		*Returns:*
			* ``None``

		*Todo:*
			* Enter thing to do. (optional field)

		*Author:*
			* Randall Hess,   12/29/2013 1:49:54 PM
		"""

		self.table_grid.ClearGrid( )
		msg = wx.grid.GridTableMessage( self.table_grid.Table, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES )
		self.table_grid.ProcessTableMessage( msg )

		# update the checked status
		self.settings_menu.Check( 201, self.remove_temp_files )
		self.settings_menu.Check( 202, self.do_triangulate )
		self.settings_menu.Check( 203, self.do_3dsmax )
		self.settings_menu.Check( 204, self.do_Maya )

		# update the mesh names list
		if self.mesh_names:
			self.mesh_list.SetItems( self.mesh_names )
			self.mesh_list.SetSelection( self.mesh_selection )
			self.selected_mesh = self.mesh_selection

		else:
			self.mesh_list.SetItems( [ ] )

		# set default text values
		self.fbx_text.SetValue( ' ' )
		self.rig_text.SetValue( '*.rigx' )
		self.cmesh_text.SetValue( '*.cmeshx' )
		self.matlib_text.SetValue( '*.matlibx' )
		self.morph_text.SetValue( '*.morphx' )

		# default all buttons to off and disabled
		self.rig_text.Enable( False )
		self.matlib_text.Enable( False )
		self.cmesh_text.Enable( False )
		self.morph_text.Enable( False )
		self.package_text.Enable( False )

		self.rig_button.Enable( False )
		self.cmesh_button.Enable( False )
		self.matlib_button.Enable( False )
		self.morph_button.Enable( False )
		self.package_folder_button.Enable( False )
		self.package_button.Enable( False )

		is_static_mesh = False
		if not self.selected_mesh is None:

			has_bone_weights = self.bone_weights[ self.selected_mesh ]
			if not has_bone_weights:
				is_static_mesh = True

			# fill out the mesh info
			self.text_triangle_count.SetLabel( '  Triangles: {0}'.format( len( self.mesh_data[ self.selected_mesh ] ) ) )
			self.text_vertex_count.SetLabel( '  Vertices: {0}'.format( len( self.vertices[ self.selected_mesh ] ) ) )
			self.text_uv_count.SetLabel( '  UVs: {0}'.format( len( self.vertices[ self.selected_mesh ] ) ) )
			self.text_material_count.SetLabel( '  Materials: {0}'.format( len( self.materials[ self.selected_mesh ] ) ) )
			self.text_collider_count.SetLabel( '  Colliders: {0}'.format( len( self.colliders[ self.selected_mesh ] ) ) )
			self.text_bone_count.SetLabel( '  Bones: {0}'.format( len( self.bones ) ) )
			self.text_tag_count.SetLabel( '  Tags: {0}'.format( len( self.tags ) ) )

			# update the material grid
			if self.materials:
				if self.materials[ self.selected_mesh ]:
					self.material_names = [ ]
					for mat_idx in range( len( self.materials[ 0 ] ) ):
						mat_name = self.materials[ 0 ][ mat_idx ].name
						self.material_names.append( mat_name )
						self.table_grid.SetCellValue( mat_idx, 1, mat_name )
						self.table_grid.SetReadOnly( mat_idx, 2, isReadOnly = False )

		else:

			# clear out the mesh info
			self.text_triangle_count.SetLabel( '  Triangles: {0}'.format( '' ) )
			self.text_vertex_count.SetLabel( '  Vertices: {0}'.format( '' ) )
			self.text_uv_count.SetLabel( '  UVs: {0}'.format( '' ) )
			self.text_material_count.SetLabel( '  Materials: {0}'.format( '' ) )
			self.text_collider_count.SetLabel( '  Colliders: {0}'.format( '' ) )
			self.text_bone_count.SetLabel( '  Bones: {0}'.format( '' ) )
			self.text_tag_count.SetLabel( '  Tags: {0}'.format( '' ) )

			# clear out the material table values
			num_rows = len ( self.table_grid.Table.data )
			for row_idx in range( num_rows ):
				#self.table_grid.SetCellValue( row_idx, 0, str( row_idx ) )
				for col in range( 1, 3 ):
					self.table_grid.SetCellValue( row_idx, col, '' )
					self.table_grid.SetReadOnly( row_idx, col, isReadOnly = True )


		if self.fbx_file:
			file_dir = os.path.dirname( self.fbx_file )
			self.fbx_text.SetValue( self.fbx_file )

			# set the conversion file paths
			if not self.selected_mesh is None:
				mesh_name = self.mesh_names[ self.selected_mesh ]
				if mesh_name:

					# set the default paths if not defined
					if is_static_mesh:
						if self.smeshx_files[ self.selected_mesh ] is None:
							smeshx_name = mesh_name + '.smeshx'
							self.smeshx_files[ self.selected_mesh ] = os.path.join( file_dir, smeshx_name )
						if self.matlibx_files[ self.selected_mesh ] is None:
							mat_name = mesh_name + '_high.matlibx'
							self.matlibx_files[ self.selected_mesh ] = os.path.join( file_dir, mat_name )

					else:
						if self.cmeshx_files[ self.selected_mesh ] is None:
							cmeshx_name = mesh_name + '.cmeshx'
							self.cmeshx_files[ self.selected_mesh ] = os.path.join( file_dir, cmeshx_name )

						if self.matlibx_files[ self.selected_mesh ] is None:
							mat_name = mesh_name + '_high.matlibx'
							self.matlibx_files[ self.selected_mesh ] = os.path.join( file_dir, mat_name )

						if self.rigx_files[ self.selected_mesh ] is None:
							rig_name = mesh_name + '.rigx'
							self.rigx_files[ self.selected_mesh ] = os.path.join( file_dir, rig_name )

						if self.morphx_files[ self.selected_mesh ] is None:
							morph_name = mesh_name + '_pc.morphx'
							self.morphx_files[ self.selected_mesh ] = os.path.join( file_dir, morph_name )
					# toggle buttons and text fields
					if is_static_mesh:
						self.cmesh_button.SetLabelText( 'Smeshx' )
						self.cmesh_text.SetValue( self.smeshx_files[ self.selected_mesh ] )
						self.cmesh_button.Enable( True )
						self.cmesh_text.Enable( True )
						self.matlib_button.Enable( True )
						self.matlib_button.SetValue( False )
						self.matlib_text.SetValue( self.matlibx_files[ self.selected_mesh ] )
						self.matlib_text.Enable( True )
						self.rig_button.SetValue( False )

					else:
						self.cmesh_button.SetLabelText( 'Cmeshx' )
						self.cmesh_button.Enable( True )
						self.cmesh_text.Enable( True )
						self.matlib_button.Enable( True )
						self.matlib_text.Enable( True )
						self.rig_button.Enable( True )
						self.rig_text.Enable( True )
						self.cmesh_text.SetValue( self.cmeshx_files[ self.selected_mesh ] )
						self.matlib_text.SetValue( self.matlibx_files[ self.selected_mesh ] )
						self.rig_text.SetValue( self.rigx_files[ self.selected_mesh ] )
						if not self.blendshapes[ self.selected_mesh ] is None:
							self.morph_button.Enable( True )
							self.morph_text.Enable( True )
							self.morph_text.SetValue( self.morphx_files[ self.selected_mesh ] )


					self.package_folder_button.Enable( True )
					if self.game_folder:
						if os.path.lexists( self.game_folder ):
							self.package_text.Enable( True )
							self.package_text.SetLabelText( self.game_folder )
							self.package_button.Enable( True )

		self.Layout( )
		self.Refresh( )
		self.SendSizeEvent( )
		self.SetFocus( )


	def on_exit( self, event ):
		"""
		Safely close the app

		*Arguments:*
			* ``event`` event id

		*Keyword Arguments:*
			* ``None``

		*Returns:*
			* ``None``

		*Author:*
			* Randall Hess,   12/28/2013 11:42:52 PM
		"""

		self.Close( True )



class FBX_Converter( wx.App ):
	"""
	Main app to run the fbx conversion

	*Arguments:*
		* ``None``

	*Keyword Arguments:*
		* ``None``

	*Returns:*
		* ``Value`` If any, enter a description for the return value here.

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   12/28/2013 9:14:23 PM
	"""

	def OnInit( self ):
		"""
		Setup the FBX Converter app

		*Arguments:*
			* ``None``

		*Keyword Arguments:*
			* ``None``

		*Returns:*
			* ``None``

		*Examples:* ::

			Enter code examples here. (optional field)

		*Todo:*
			* Enter thing to do. (optional field)

		*Author:*
			* Randall Hess,   12/28/2013 9:12:37 PM
		"""

		frame = App_Frame( None, -1 )
		frame.Show( True )
		self.SetTopWindow( frame )

		return True


if __name__ == '__main__':
	app = FBX_Converter( )
	app.MainLoop( )