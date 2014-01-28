"""
Volition FBX Converter

Import an FBX file
- Convert to Saints Row Files
-- Character Mesh ( *.cmeshx )
-- Skeleton File  ( *.rigx )
-- Material Library ( *.matlibx )

"""

import os
import sys
import struct
import xml.dom.minidom
import xml.etree.cElementTree
import wx
import wx.grid as gridlib

import FbxCommon


DEBUG_OUTPUT = False

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
                  }


class Node_Bone( object ):
	"""
	Fbx bone object

	*Arguments:*
		* ``node`` Fbx node for the bone
	* ``scene`` Fbx scene
	* ``coordinate_system_transform`` transform for the game coordinate system

	*Keyword Arguments:*
		* ``none``

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   11/19/2013 9:27:47 PM
	"""

	def __init__( self, node, scene, coordinate_system_transform ):
		self.node       = node
		self.name       = node.GetName( )
		self.id         = None
		self.index      = None
		self.parent     = None
		self.parent_id  = None
		self.parent_index = None

		object_transform = compute_world_transform( node, coordinate_system_transform )
		self.quat = object_transform.GetQ( )
		self.pos  = object_transform.GetT( )

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
		print 'IN: Bone index: {0} Bone id: {1} Parent: {2} Parent id: {3}'.format( self.index, self.id, self.parent, self.parent_id )

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

		print 'OUT: Bone index: {0} Bone id: {1} Parent: {2} Parent id: {3}'.format( self.index, self.id, self.parent, self.parent_id )


class Node_Tag( object ):
	"""
	Fbx tag object

	*Arguments:*
		* ``node`` Fbx node for the bone
	* ``scene`` Fbx scene
	* ``coordinate_system_transform`` transform for the game coordinate system

	*Keyword Arguments:*
		* ``none``

	*Examples:* ::

		Enter code examples here. (optional field)

	*Todo:*
		* Enter thing to do. (optional field)

	*Author:*
		* Randall Hess,   11/19/2013 9:27:47 PM
	"""

	def __init__( self, node, scene, coordinate_system_transform ):
		self.node    = node
		self.name    = node.GetName( )
		self.parent  = node.GetParent( )
		self.parent_index = 0

		# get the transform then remove the scale from the tags
		object_transform = compute_world_transform( node, coordinate_system_transform )
		object_transform = remove_transform_scale( object_transform )

		# get the rotation
		self.quat = object_transform.GetQ( )

		# get the position relative to the parent
		parentNode = node.GetParent()
		parent_object_transform = compute_world_transform( parentNode, coordinate_system_transform )
		self.pos  = object_transform.GetT( ) - parent_object_transform.GetT( )



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
		self.diffuse_map = 'missing.tga'
		self.normal_map = 'normal_blank_n.tga' #'flat-normalmap_n.tga'
		self.normal_map_height = 1.000000
		self.specular_map = 'spec_blank_s.tga'
		self.specular_map_amount = 1.000000
		self.specular_power = 60.000000
		self.specular_power2 = 60.000000
		self.specular_alpha = 0.000000
		self.specular_alpha2 = 0.000000
		self.specular_alpha_interface = 1.000000
		self.specular_alpha_interface2 = 0.000000
		self.sphere_map1 = 'missing-grey.tga'
		self.sphere_map2 = 'missing-grey.tga'
		self.sphere_map_amount = 1.000000
		self.pattern = 'missing.tga'
		self.dob = 'missing.tga'
		self.blend_map = 'shd_whiteopaque.tga'
		self.shader = 'ir_bbsimple3'
		self.base_opacity = 1.000000
		self.texture = 'norender.tga'
		self.fresnel_alpha_interface = 0.000000
		self.fresnel_alpha_interface2 = 0.000000
		self.fresnel_strength = 0.000000
		self.fresnel_strength2 = 0.000000
		self.self_illumination = 0.000000
		self.xml_element = None
		self.pattern_map = 'missing-black.tga'


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
	Get a list of shaders from the given xml file

	*Arguments:*
		* ``xml_file`` Shader xml file

	*Returns:*
		* ``list`` list of shader names

	*Author:*
		* Randall Hess, , 1/2/2014 5:42:31 PM
	"""

	if not os.path.lexists( xml_file ):
		wx.MessageBox( 'Xml Shaders file is missing!\n' + xml_file, style = wx.OK )
		return [ ], { }

	shader_names = [ ]
	material_elements = { }
	try:
		xml_doc = xml.etree.cElementTree.parse( xml_file )
	except:
		wx.MessageBox( 'Could not parse ' + xml_file, style = wx.OK )
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
	              '.texture' : 'texture' }

	crunch_targets = { '.matlibx' : [ '.matlib_' ],
	            '.cmeshx' : [ '.ccmesh_', '.gcmesh_', '.morph_key_' ],
	            '.rigx' : [ '.rig_' ],
	            '.peg' : [ '.cpeg_', '.gpeg_' ],
	            '.texture' : [ '.cvbm_', '.gvbm_', '.acl_' ] }

	crunch_names = { '.rigx' : 'rig_cruncher_wd_',
	                 '.cmeshx' : 'mesh_crunch_wd_',
	                 '.peg' : 'peg_assemble_wd_',
	                 '.matlibx' : 'material_library_crunch_wd_',
	                 '.texture' : 'texture_crunch_wd_' }

	texture_types = { '.peg' : [ '.cvbm_', '.gvbm_' ] }


	platform = 'pc'
	header = xml.etree.cElementTree.Element( 'ctg' )
	in_platforms = xml.etree.cElementTree.SubElement( header, 'in_platforms' )
	cur_platform = xml.etree.cElementTree.SubElement( in_platforms, 'platform' )
	cur_platform.text = platform
	base_name = None
	base_no_ext = None

	if not resource_type == '.peg':

		# write the source filename
		source = xml.etree.cElementTree.SubElement( cur_platform, 'source' )
		if resource_type == '.texture':
			base_name = os.path.basename( textures )
			source.text = textures
		else:
			base_name = os.path.basename( filename )
			source.text = filename
		base_no_ext = os.path.splitext( base_name )[ 0 ]


		if not resource_type == '.texture':

			# first attr
			attr = xml.etree.cElementTree.SubElement( source, 'attr' )
			display_name = xml.etree.cElementTree.SubElement( attr, 'display_name' )
			display_name.text = 'Name'
			val = xml.etree.cElementTree.SubElement( attr, 'val' )
			val.text = base_no_ext + resource_type

			# second attr
			attr1 = xml.etree.cElementTree.SubElement( source, 'attr' )
			display_name1 = xml.etree.cElementTree.SubElement( attr1, 'display_name' )
			display_name1.text = 'Resource Type'
			val1 = xml.etree.cElementTree.SubElement( attr1, 'val' )
			val1.text = resources[ resource_type ]

			# TO-DO handle additional attrs.. ( texture_is_linear_color_space, normal_map )

	else:
		data_types = texture_types[ resource_type ]
		for texture in textures:
			for data in data_types:
				base_name = os.path.basename( texture )
				base_no_ext = os.path.splitext( base_name )[ 0 ]
				base_data_ext = base_no_ext + data + platform
				source = xml.etree.cElementTree.SubElement( cur_platform, 'source' )
				source.text = os.path.join( os.path.dirname( texture ), base_data_ext )

				#if resource_type == '.peg':
					## first attr
					#attr = xml.etree.cElementTree.SubElement( source, 'attr' )
					#display_name = xml.etree.cElementTree.SubElement( attr, 'display_name' )
					#display_name.text = 'Name'
					#val = xml.etree.cElementTree.SubElement( attr, 'val' )
					#if resource_type == '.texture':
						#val.text = base_name
					#else:
						#val.text = base_data_ext

					## second attr
					#attr1 = xml.etree.cElementTree.SubElement( source, 'attr' )
					#display_name1 = xml.etree.cElementTree.SubElement( attr1, 'display_name' )
					#display_name1.text = 'Resource Type'
					#val1 = xml.etree.cElementTree.SubElement( attr1, 'val' )
					#val1.text = resources[ resource_type ]

					## TO-DO handle additional attrs.. ( texture_is_linear_color_space, normal_map )

	# output target files
	targets = crunch_targets[ resource_type ]
	for target in targets:
		temp_target = xml.etree.cElementTree.SubElement( cur_platform, 'target' )
		if resource_type == '.peg':
			base_name = os.path.basename( filename )
			base_no_ext = os.path.splitext( base_name )[ 0 ]
			target_filename = base_no_ext + target + platform
		else:
			target_filename =  base_no_ext + target + platform
		temp_target.text = os.path.join( os.path.dirname( filename ), target_filename )

	if resource_type == '.texture' or resource_type == '.peg':
		log = xml.etree.cElementTree.SubElement( header, 'log' )
		log.text = os.path.join( os.path.dirname( filename ), ( 'log_' + base_no_ext + '_' + resources[ resource_type ] + '.txt' ) )
		warnings_as_errors = xml.etree.cElementTree.SubElement( header, 'warnings_as_errors' )
		warnings_as_errors.text = 'true'
		errors_are_fatal = xml.etree.cElementTree.SubElement( header, 'errors_are_fatal' )
		errors_are_fatal.text = 'true'
	else:
		output = xml.etree.cElementTree.SubElement( header, 'output' )
		output.text =  os.path.join( os.path.dirname( filename ), 'log1_' + base_no_ext + '_' + resources[ resource_type ] + '.txt' )
		log = xml.etree.cElementTree.SubElement( header, 'log' )
		log.text = os.path.join( os.path.dirname( filename ), 'log2_' + base_no_ext + '_' + resources[ resource_type ] +  '.txt' )
		project = xml.etree.cElementTree.SubElement( header, 'project' )
		project.text = 'SR3'
		add_args = xml.etree.cElementTree.SubElement( header, 'additional_args' )
		add_args.text = ' '
		output_flags = xml.etree.cElementTree.SubElement( header, 'output_flags' )
		output_flags.text = 'ctg,file'
		timeout_msec = xml.etree.cElementTree.SubElement( header, 'timeout_msec' )
		timeout_msec.text = '1800000'
		silent_verror = xml.etree.cElementTree.SubElement( header, 'silent_verror' )
		silent_verror.text = 'true'
		warnings_as_errors = xml.etree.cElementTree.SubElement( header, 'warnings_as_errors' )
		warnings_as_errors.text = 'true'
		errors_are_fatal = xml.etree.cElementTree.SubElement( header, 'errors_are_fatal' )
		errors_are_fatal.text = 'true'
		out_platforms = xml.etree.cElementTree.SubElement( header, 'out_platforms' )
		out_platforms.text = ' '
		out_rules = xml.etree.cElementTree.SubElement( header, 'out_rules' )
		out_rules.text = ' '

	# write out the mesh crunch rule file
	rule_xml = pretty_xml( header )
	crunch_name = crunch_names[ resource_type ] + platform + '_' + base_no_ext + '.rule'
	crunch_file =  os.path.join( os.path.dirname( filename ), crunch_name )
	with open( crunch_file, 'w' ) as crunch_rule:
		crunch_rule.write( rule_xml )


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


def write_cmeshx( filename, mesh, mesh_name, face_data, vertices, bone_order, tags, materials, bone_weights ):
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
		cmeshx_file.write( '\t\t<rig_version>1</rig_version>\n' )
		cmeshx_file.write( '\t</header>\n' )

		# write bones
		bones = { }
		index = 0
		cmeshx_file.write( '\t<bones>\n' )
		for bone_index in sorted( bone_order ):
			bone = bone_order[ bone_index ]
			bones[ bone.name ] = index
			cmeshx_file.write( '\t\t<bone>\n' )
			cmeshx_file.write( '\t\t\t<name>{0}</name>\n'.format( bone.name.lower() ) )
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
			cmeshx_file.write( '\t\t\t<name>{0}</name>\n'.format( tag.name.lower() ) )
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
		for face in face_data:
			vert_idx = 0
			for vert_data in face.verts:
				# make sure we haven't already written this vertex index
				if not vert_data.index in vert_indices:
					face.indices[ vert_idx ] = vert_index

					vert_indices.append( vert_data.index )
					vert = vert_data.positions

					if DEBUG_OUTPUT:
						cmeshx_file.write( '\t\t\t\t{0}         {1}        {2}\n'.format( round( -vert[0], 5 ),  round( vert[2], 5 ), round( -vert[1], 5 ) ) )

					# convert the vertex floats into hex
					vert_x = get_float_as_hex( -vert[ 0 ] )
					vert_y = get_float_as_hex( vert[ 2 ] )
					vert_z = get_float_as_hex( -vert[ 1 ] )

					# write out the converted vertex
					cmeshx_file.write( '\t\t\t\t<v>{0} {1} {2}</v>\n'.format( vert_x, vert_y, vert_z, vert_index ) )

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


		# **************************************************************
		# Vertex Weights
		cmeshx_file.write( '\t\t\t<vertexweights>\n' )
		cmeshx_file.write( '\t\t\t\t<numvweights>{0}</numvweights>\n'.format( len( vertices ) ) )
		cmeshx_file.write( '\t\t\t\t<vweights>\n' )


		# **************************************************************
		# Bone Weights

		## get the vert/weight info
		#bone_weights = get_boneweights( lmesh, vertices )

		# Get the vertex weights relative to boneIndices above
		for vert_index, weight_info in bone_weights.iteritems( ):

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

			# TO-DO sort by lowest bone index, 1 - n
			cmeshx_file.write( '\t\t\t\t\t<weight>{0:d} {1:d} {2:d} {3:d} {4:d} {5:d} {6:d} {7:d}</weight>\n'.format( weight_values[0], weight_values[1], weight_values[2], weight_values[3], weight_values[4], weight_values[5], weight_values[6], weight_values[7] ) )
		cmeshx_file.write( '\t\t\t\t</vweights>\n' )
		cmeshx_file.write( '\t\t\t</vertexweights>\n' )

		# Close Mesh Block
		cmeshx_file.write( '\t\t</mesh>\n' )

		# Auto Generate LODs
		cmeshx_file.write( '\t<AutoGenerateLODs>true</AutoGenerateLODs>\n' )

		# TODO - See if we actually use this
		# LOD flags
		cmeshx_file.write( '\t<LODParameterOverrides>\n' )
		cmeshx_file.write( '\t</LODParameterOverrides>\n' )

		# close the xml
		cmeshx_file.write( '</root>' )

		return True

	# writing file failed
	return False


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
			rig_file.write( '\t\t\t<name>{0}</name>\n'.format( bone.name.lower() ) )
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
			rig_file.write( '\t\t\t<name>{0}</name>\n'.format( tag.name.lower() ) )
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
					if DEBUG_OUTPUT:
						print 'Material Element: {0}, Material Value: {1}'.format( element.tag, element_value )
				else:
					element_value = ''

			file_.write( '{0}<{1}>{2}</{1}>\n'.format( tabs, element.tag, element_value ) )
	else:
		wx.MessageBox( ' Material is missing an assigned shader!\nMaterial: ' + material.name , style = wx.OK )
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


def get_boneweights( mesh, vertices ):
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

	bones = {}

	number_skin_deformers= mesh.GetDeformerCount( FbxCommon.FbxDeformer.eSkin )
	for skin_index in range( number_skin_deformers ):
		cluster_count = mesh.GetDeformer( skin_index, FbxCommon.FbxDeformer.eSkin ).GetClusterCount( )
		for cluster_index in range( cluster_count ):
			cluster = mesh.GetDeformer( skin_index, FbxCommon.FbxDeformer.eSkin ).GetCluster( cluster_index )

			# get the current bone/link name
			bone_name = None
			if cluster.GetLink( ):
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
					for vert in vertices:
						if vert.index == indice:
							if DEBUG_OUTPUT:
								print 'Vert index {0} is indice: {1}'.format( vert.index, indice )
							bone_weights[ indice ][ bone_name ] = lWeights[ index ]



						elif not vert.original_index == -1 and vert.original_index == indice:
							if DEBUG_OUTPUT:
								print 'Vert original index {0} is indice: {1}'.format( vert.index, indice )
							bone_weights[ vert.index ][ bone_name ] = lWeights[ index ]
					index += 1

	# print out the vert_dict
	assert isinstance( bone_weights, dict )

	if DEBUG_OUTPUT:
		print '\n----------------'
		print 'Vertex Weights'
		print '----------------'
		for key, value in bone_weights.iteritems( ):
			print ' vert: {0}    weights: {1}'.format( key, value )
		print '\n'

	return bone_weights, bones


def get_mesh_data( lmesh, coordinate_system_transform ):
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

	scale_inches_to_meters = 39.3701

	# TODO - Handle Multiple Layers
	layer_element = lmesh.GetLayer( 0 )
	if layer_element:

		num_verts = lmesh.GetControlPointsCount( )

		# setup the vert data
		vertices = [ ]
		for i in range( num_verts ):
			vertices.append( Vertex_Info( i ) )

		# get the fbx verts
		fbx_verts = [ ]
		control_points = lmesh.GetControlPoints( )
		for vert_index in range( num_verts ):
			vert = control_points[ vert_index ]
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

			# create the face object
			face = Face_Info( triangle_index )

			# get the material id for the current face
			if material_element:
				material_id = material_element.GetIndexArray( ).GetAt( triangle_index )
				face.material_id = material_id

			for idx in range( 0, 3 ):

				# triangle, Vertices
				index = lmesh.GetPolygonVertex( triangle_index, idx )

				# setup a temp info
				temp_vert = Vertex_Info( index )
				temp_vert.index = index
				temp_vert.positions[ 0 ] = fbx_verts[ index ][ 0 ]
				temp_vert.positions[ 1 ] = fbx_verts[ index ][ 1 ]
				temp_vert.positions[ 2 ] = fbx_verts[ index ][ 2 ]

				# triangle, Normals
				fbx_norm = FbxCommon.FbxVector4()
				lmesh.GetPolygonVertexNormal( triangle_index, idx, fbx_norm )
				temp_vert.normal[ 0 ] = get_scaled_value( fbx_norm[ 0 ], 1.0 )
				temp_vert.normal[ 1 ] = get_scaled_value( fbx_norm[ 1 ], 1.0 )
				temp_vert.normal[ 2 ] = get_scaled_value( fbx_norm[ 2 ], 1.0 )

				# triangle, UVs
				tex_coord_found = False
				fbx_uv = FbxCommon.FbxVector2()
				tex_coord_found = lmesh.GetPolygonVertexUV( triangle_index, idx, uv_name, fbx_uv )
				temp_vert.uvs[ 0 ] = get_scaled_value( fbx_uv[ 0 ], 1.0 )
				temp_vert.uvs[ 1 ] = 1.0 - ( get_scaled_value( fbx_uv[ 1 ], 1.0 ) ) #( get_scaled_value( fbx_uv[ 1 ], 1.0 ) )

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

						if found_vert:
							pass

						else:
							# create a new vert
							temp_index = len( vertices) + 1
							temp_vert.index = temp_index
							temp_vert.original_index = index
							vertices.append( temp_vert )
							if DEBUG_OUTPUT:
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
				index = 0
				for vert in face.verts:
					print '  UV {0}: {1}'.format( index, vert.uvs )
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


def load_fbx_scene( fbx_scene ):
	"""
	Load the FBX scene and do necessary conversions

	*Arguments:*
		* ``fbx_scene`` Fbx scene file

	*Keyword Arguments:*
		* ``none``

	*Returns:*
	   * ``lStatus`` Status of opening the fbx_scene
	* ``lScene`` Initialized fbx_scene
		* ``coordinate_system_transform`` transform to conver to game coordinate system
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
		target_axis = FbxCommon.FbxAxisSystem.eMax
		if not lScene.GetGlobalSettings( ).GetAxisSystem( ) is target_axis:
			FbxCommon.FbxAxisSystem.Max.ConvertScene( lScene )

		fbxUnits			= lScene.GetGlobalSettings( ).GetSystemUnit( )
		fbxAxis			= lScene.GetGlobalSettings( ).GetAxisSystem( )
		fbx_evaluator	= FbxCommon.FbxScene.GetEvaluator( lScene )

		# GetScaleFactor gets the system units converted to cm, convert those to meters for game
		scene_scale_conversion = fbxUnits.GetScaleFactor( ) * 0.01

		# Convert the axis system
		# grab the up vector
		up_vector_sign 	= 0
		front_vector_sign = 1

		# GetFrontVector is missing from Fbx Python SDK -2014.1, Should be there in 2014.2
		#fbxAxis.GetFrontVector( front_vector_sign )
		front_vector_type			= FbxCommon.FbxAxisSystem.eParityOdd
		up_vector_type, up_vector_sign = fbxAxis.GetUpVector( )
		coordinate_system_type	= fbxAxis.GetCoorSystem( )

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
		coordinate_system_transform.SetColumn( 0, -right_vector )	#RVec
		coordinate_system_transform.SetColumn( 1, up_vector )			#UVec
		coordinate_system_transform.SetColumn( 2, front_vector )		#FVec
		coordinate_system_transform.SetColumn( 3, FbxCommon.FbxVector4( ) )	#Position

		## reflect the matrix for coordinate system transform, if going from right to left handed
		#if coordinate_system_type == FbxAxisSystem.eRightHanded:
			#rvec = FbxVector4( )
			#rvec.Set( 1.0, 0.0, 0.0, 0.0 )
			#uvec = FbxVector4( )
			#uvec.Set( 0.0, 1.0, 0.0, 0.0 )
			#fvec = FbxVector4( )
			#fvec.Set( 0.0, 0.0, -1.0, 0.0 )
			#row4 = FbxVector4( )

			#reflection_matrix = FbxMatrix( )
			#reflection_matrix.SetColumn( 0, rvec )
			#reflection_matrix.SetColumn( 1, uvec )
			#reflection_matrix.SetColumn( 2, fvec )
			#reflection_matrix.SetColumn( 3, row4 )

			#coordinate_system_transform = coordinate_system_transform * reflection_matrix

		# get the scale matrix
		scale_matrix = FbxCommon.FbxMatrix( )
		scale_matrix.SetIdentity( )
		scale_col0 = scale_matrix[0]
		scale_col1 = scale_matrix[1]
		scale_col2 = scale_matrix[2]

		rvec = FbxCommon.FbxVector4( )
		rvec.Set( scene_scale_conversion, scale_col0[1], scale_col0[2], scale_col0[3] )
		uvec = FbxCommon.FbxVector4( )
		uvec.Set( scale_col1[0], scene_scale_conversion, scale_col1[2], scale_col1[3] )
		fvec = FbxCommon.FbxVector4( )
		fvec.Set( scale_col2[0], scale_col2[1], scene_scale_conversion, scale_col2[3] )

		scale_matrix.SetColumn( 0, rvec )
		scale_matrix.SetColumn( 1, uvec )
		scale_matrix.SetColumn( 2, fvec )

		coordinate_system_transform = coordinate_system_transform * scale_matrix

		# This matrix needs to be inverted/transposed for the math to work throughout the cruncher.
		coordinate_system_transform.Transpose( )

		return lStatus, lScene, coordinate_system_transform, lSdkManager

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

	scene_scale_conversion = 0.0254

	# build up the vectors with the scale conversion
	rvec = FbxCommon.FbxVector4( )
	rvec.Set( scene_scale_conversion, scale_col0[1], scale_col0[2], scale_col0[3] )
	uvec = FbxCommon.FbxVector4( )
	uvec.Set( scale_col1[0], scene_scale_conversion, scale_col1[2], scale_col1[3] )
	fvec = FbxCommon.FbxVector4( )
	fvec.Set( scale_col2[0], scale_col2[1], scene_scale_conversion, scale_col2[3] )

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


def compute_world_transform( fbx_node, coordinate_system_transform, use_geom = False ):
	"""
	Taken from rlb_import_fbx_mesh.cpp
	Returns the world transform for an fbx node object.
	This includes converting it to a friendly Volition format, and accounting for a pivot offset and export origin

	*Arguments:*
		* ``fbx_node`` the current fbx object
	   * ``coordinate_system_transform`` the transform we use to convert from fbx to game

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
	coordinate_system_transform.GetElements( translation, quat, shear, scale )

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
			self.SetRowSize( row, 20 )
			for col in range( self.GetNumberCols( ) ):
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

	def __init__( self, parent, ID, title='Volition FBX Converter' ):
		wx.Frame.__init__(self, parent, ID, title, wx.DefaultPosition, wx.Size( 422, 610 ), style = wx.DEFAULT_DIALOG_STYLE)

		# FBX Scene Data
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
		self.material_elements = { }
		self.material_names = [ ]
		self.textures = [ ]
		self.shader_names = [ ]
		self.selected_mesh = None
		self.selected_material = None
		self.rigx_file = None
		self.cmeshx_file = None
		self.matlibx_file = None
		self.node_index = 0
		self.nodes = { }

		# Status Bar
		self.CreateStatusBar()
		self.SetStatusText( 'Status:   Import FBX File' )

		# Create Menu Items
		self.menu = wx.Menu()
		self.menu.Append(100, "&Import FBX", "Import FBX File (*.FBX)")
		#menu.Append(101, "&Reload file", "Import FBX File (*.FBX)")
		#menu.Append(101, "&Import File List", "Import Animation File List (*.txt)")
		self.menu.AppendSeparator()
		self.menu.Append(110, "&Exit", "Terminate the program")

		# when running as a python file dirname gets the parent directory,
		# when running as an exe, dirname is the local directory of library.zip ( strange )
		shaders_file = os.path.join( os.path.dirname( sys.path[0] ), 'sr_shaders.xml' )
		if not os.path.lexists( shaders_file ):
			shaders_file = os.path.join( sys.path[0], 'sr_shaders.xml' )

		if os.path.lexists( shaders_file ):
			self.shader_names, self.material_elements = get_shaders_from_xml( xml_file = shaders_file )
		else:
			wx.MessageBox( 'Make sure the "sr_shaders.xml" file is in the same directory as the FBX_Converter.exe', style = wx.OK )

		self.table_grid = Table_Grid( self, self.shader_names )
		self.table_grid.SetDoubleBuffered( False )
		#menu_settings = wx.Menu()
		#menu_settings.AppendRadioItem(200, "&All", "Show All Files")
		#menu_settings.AppendRadioItem(201, "&Preloaded", "Show Preloaded Files")
		#menu_settings.AppendRadioItem(202, "&Non-Preloaded", "Show Files that are not Preloaded")

		# Create MenuBar and add Menu Items
		menuBar = wx.MenuBar()
		menuBar.Append(self.menu, "&File");
		#menuBar.Append(menu_settings, "&Settings");

		self.SetMenuBar(menuBar)

		# Register the events
		wx.EVT_MENU( self, 100, self.load_fbx_file )
		wx.EVT_MENU( self, 110, self.on_exit)


		# FBX Box
		fbx_box = wx.StaticBox( self, 0, ' FBX ' )
		fbx_sizer = wx.StaticBoxSizer( fbx_box, wx.VERTICAL )
		fbx_hsizer = wx.BoxSizer( wx.HORIZONTAL )

		self.fbx_button = wx.Button( self, 3,'Import ', size = ( 50, 20 ) )
		self.fbx_button.Bind( wx.EVT_BUTTON, self.load_fbx_file )
		self.fbx_text = wx.TextCtrl( self, -1, "", size = ( 310, 21 ), style=wx.TE_READONLY  )
		self.Bind( wx.EVT_DROP_FILES, self.load_fbx_file, self.fbx_text )
		fbx_hsizer.AddSpacer( 5 )
		fbx_hsizer.Add( self.fbx_button, 0 )
		fbx_hsizer.AddSpacer( 5 )
		fbx_hsizer.Add( self.fbx_text, 0 )
		fbx_hsizer.AddSpacer( 5 )
		#fb_text = Label_Ctrl( self, text_string = "FBX", boxSize=( 390, 20), onTop = True)
		#fbx_sizer.Add( fb_text, 0, wx.TOP| wx.LEFT )
		fbx_sizer.AddSpacer( 6 )
		fbx_sizer.Add( fbx_hsizer, 0, wx.ALIGN_CENTER, border = 0 )
		fbx_sizer.AddSpacer( 5 )

		# Mesh Box
		mesh_box = wx.StaticBox( self, 1, ' MESH ' )
		mb_sizer = wx.StaticBoxSizer( mesh_box, wx.HORIZONTAL )
		mb_vSizer = wx.BoxSizer( wx.VERTICAL )

		temp_list = [ ]
		self.mesh_list = wx.ComboBox( self, 200, '', (90,50), (160,-1), temp_list, wx.CB_DROPDOWN )
		self.mesh_list.SetEditable( False )
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
		export_sizer = wx.StaticBoxSizer( export_box, wx.VERTICAL )
		export_hsizer1 = wx.BoxSizer( wx.HORIZONTAL )
		export_hsizer2 = wx.BoxSizer( wx.HORIZONTAL )
		export_hsizer3 = wx.BoxSizer( wx.HORIZONTAL )
		export_hsizer4 = wx.BoxSizer( wx.HORIZONTAL )

		self.rig_button = wx.ToggleButton( self, 3,'Rigx ', size = ( 50, 20 ) )
		self.rig_text = wx.TextCtrl( self, -1, "*.rigx", size = ( 310, 21 ), style=wx.TE_READONLY  )
		export_hsizer1.AddSpacer( 5 )
		export_hsizer1.Add( self.rig_button, 0, wx.ALIGN_CENTER )
		export_hsizer1.AddSpacer( 5 )
		export_hsizer1.Add( self.rig_text, 0 )
		export_hsizer1.AddSpacer( 5 )

		self.cmesh_button = wx.ToggleButton( self, 3,'Cmeshx ', size = ( 50, 20 ) )
		self.cmesh_text = wx.TextCtrl( self, -1, "*.cmeshx", size = ( 310, 21 ), style=wx.TE_READONLY  )

		export_hsizer2.AddSpacer( 5 )
		export_hsizer2.Add( self.cmesh_button, 0 )
		export_hsizer2.AddSpacer( 5 )
		export_hsizer2.Add( self.cmesh_text, 0 )
		export_hsizer2.AddSpacer( 5 )

		self.matlib_button = wx.ToggleButton( self, 3,'Matlibx ', size = ( 50, 20 ) )
		self.matlib_text = wx.TextCtrl( self, -1, "*.matlibx", size = ( 310, 21 ), style=wx.TE_READONLY  )
		export_hsizer3.AddSpacer( 5 )
		export_hsizer3.Add( self.matlib_button, 0 )
		export_hsizer3.AddSpacer( 5 )
		export_hsizer3.Add( self.matlib_text, 0 )
		export_hsizer3.AddSpacer( 5 )

		self.button_export = wx.Button( self, 3,'Convert ', size = ( 200, 22 ) )
		self.button_export.Bind( wx.EVT_BUTTON, self.convert_files )
		export_hsizer4.AddSpacer( 5 )
		export_hsizer4.Add( self.button_export, 0 )
		export_hsizer4.AddSpacer( 5 )

		#mat_text = Label_Ctrl( self, text_string = "Convert", boxSize=( 390, 20), onTop = True)
		#export_sizer.Add( mat_text, 0, wx.TOP )
		export_sizer.AddSpacer( 6 )
		export_sizer.Add( export_hsizer1, 0 )
		export_sizer.AddSpacer( 5 )
		export_sizer.Add( export_hsizer2, 0 )
		export_sizer.AddSpacer( 5 )
		export_sizer.Add( export_hsizer3, 0 )
		export_sizer.AddSpacer( 15 )
		export_sizer.Add( export_hsizer4, 0, wx.ALIGN_CENTER_HORIZONTAL )
		export_sizer.AddSpacer( 5 )

		# Setup Layout
		self.mSizer = wx.BoxSizer(wx.VERTICAL)
		hSizer = wx.BoxSizer(wx.HORIZONTAL)
		vSizer = wx.BoxSizer(wx.VERTICAL)
		vSizer.AddSpacer( 7 )
		vSizerB = wx.BoxSizer(wx.VERTICAL)
		vSizerB.AddSpacer( 7 )
		vSizerB.Add( bsizer )
		sizer = wx.BoxSizer( wx.VERTICAL )
		sizer.AddSpacer( 5 )
		sizer.Add( fbx_sizer, 0, wx.BOTTOM )
		sizer.AddSpacer( 7 )
		sizer.Add( mb_sizer, 0, wx.TOP )
		sizer.AddSpacer( 7 )
		sizer.Add( export_sizer, 0, wx.TOP )
		sizer.AddSpacer( 10 )
		vSizer.Add( sizer, 0, wx.ALIGN_LEFT )
		hSizer.AddSpacer( 15 )
		hSizer.Add( vSizer, 0, wx.ALIGN_LEFT )
		hSizer.AddSpacer( 30 )
		hSizer.Add( vSizerB,0, wx.ALIGN_TOP )
		self.mSizer.Add( hSizer,0, wx.ALIGN_TOP )
		self.mSizer.AddSpacer( 20 )

		self.SetSizer( self.mSizer )
		#self.Layout( )
		self.update_ui( )


	def convert_files( self, event ):
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
			wx.MessageBox( 'A mesh has not been selected to convert!' + '\n\nAborting Conversion' , style = wx.OK )
			return False

		for index in range( len( self.materials[ self.selected_mesh ] ) ):
			shader_value = self.table_grid.GetCellValue( index, 2 )
			if shader_value:
				self.materials[ self.selected_mesh ][ index ].shader = shader_value
				self.materials[ self.selected_mesh ][ index ].xml_element = self.material_elements[ shader_value ]
				if DEBUG_OUTPUT:
					print 'Material: {0} Shader: {1} XML_Element: {2}'.format( index, shader_value, self.material_elements[ shader_value ] )
			else:
				wx.MessageBox( 'Material is missing an assigned shader!\nMaterial: ' + self.materials[ self.selected_mesh ][ index ].name + '\n\nAborting Conversion' , style = wx.OK )
				return False

		did_convert = False
		write_rigx_file = False
		write_cmeshx_file = False
		write_matlibx_file = False
		if self.rig_button.GetValue( ):
			if DEBUG_OUTPUT:
				print("\n\n------------\nWrite Rigx\n------------\n")
			write_rigx_file = write_rigx( self.rigx_file, self.bone_orders[ self.selected_mesh ], self.tags )
			if write_rigx_file:
				did_convert = True
				print 'Rigx file was written'
				write_crunch_rule( self.rigx_file, '.rigx' )

		if self.cmesh_button.GetValue( ):
			write_cmeshx_file = write_cmeshx( self.cmeshx_file, self.meshes[ self.selected_mesh ], self.mesh_names[ self.selected_mesh ], self.mesh_data[ self.selected_mesh ], self.vertices[ self.selected_mesh ], self.bone_orders[ self.selected_mesh ], self.tags, self.materials[ self.selected_mesh ], self.bone_weights[ self.selected_mesh ] )
			if write_cmeshx_file:
				did_convert = True
				print 'Cmeshx file was written'
				write_crunch_rule( self.cmeshx_file, '.cmeshx' )

		if self.matlib_button.GetValue( ):
			write_matlibx_file = write_matlibx( self.matlibx_file, self.materials[ self.selected_mesh ] )
			if write_matlibx_file:
				did_convert = True
				print 'Matlibx file was written'
				write_crunch_rule( self.matlibx_file, '.matlibx' )

		# write out the peg rule
		if write_cmeshx_file or write_matlibx_file:

			# write a rule for each texture file
			for texture in self.textures[ self.selected_mesh ]:
				write_crunch_rule( self.fbx_file, '.texture', textures = texture )

			write_crunch_rule( self.fbx_file, '.peg', textures = self.textures[ self.selected_mesh ] )

		self.SetSizer( self.mSizer )
		self.SetFocus( )

		if not did_convert:
			wx.MessageBox( 'Nothing was selected to convert!', style = wx.OK )
		else:
			wx.MessageBox( 'Conversion completed!', style = wx.OK )

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
		self.selected_mesh = None
		self.selected_material = None

		self.update_ui( )


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

		*Examples:* ::

			Enter code examples here. (optional field)

		*Todo:*
			* Enter thing to do. (optional field)

		*Author:*
			* Randall Hess,   12/28/2013 9:28:01 PM
		"""

		fbx_file = None
		self.reset_variables( )

		self.SetStatusText( 'Importing FBX File ...' )

		# pick the fbx file
		open_dialog = wx.FileDialog( self, message = 'Choose a file', defaultDir = 'c:', defaultFile='', wildcard = 'Autodesk FBX (*.FBX)|*.fbx' )
		if open_dialog.ShowModal() == wx.ID_OK:
			fbx_file = open_dialog.GetPath( )
		open_dialog.Destroy()

		if fbx_file:

			self.fbx_file = fbx_file

			# get the fbx file location and name
			file_dir = os.path.dirname( self.fbx_file )
			base_name = os.path.basename( self.fbx_file )
			base_no_ext = os.path.splitext( base_name )[ 0 ]

			# set the conversion file paths
			rig_name = base_no_ext + '.rigx'
			self.rigx_file = os.path.join( file_dir, rig_name )
			cmesh_name = base_no_ext + '.cmeshx'
			self.cmeshx_file = os.path.join( file_dir, cmesh_name )
			matlib_name = base_no_ext + '.matlibx'
			self.matlibx_file = os.path.join( file_dir, matlib_name )

			# Load the fbx scene
			fbx_status, fbx_scene, coordinate_system_transform, lSdkManager = load_fbx_scene( fbx_file )
			if fbx_status:

				if DEBUG_OUTPUT:
					print("\n\n---------\nGet Scene Hierarchy\n---------\n")

				self.SetStatusText( 'Getting the FBX Hierarchy ...' )
				self.get_fbx_hierarchy( fbx_scene, coordinate_system_transform )

				if DEBUG_OUTPUT:
					print("\n\n------------\nGet Bone Hierarchy\n------------\n")

				# Filter out any mesh objects that might be acting as bones
				# remove any of those "bones" from the mesh list
				for mesh in self.meshes:
					lmesh = mesh.GetNodeAttribute( )

					# get the vert/weight info
					self.SetStatusText( 'Getting Mesh Bone Weights: {0}'.format( mesh.GetName( ) ) )
					bone_weights, bones = get_boneweights( lmesh, [ ] )
					#self.bone_weights.append( bone_weights )

					# determine if bones found in bone weights are in the self.meshes list
					# if they are in the self.meshes list, we need to remove them,
					# we also need to create_bones from these objects
					for bone_name, bone_node in bones.iteritems( ):
						print 'Mesh: {0} Bone Name: {1} Bone Node: {2}'.format( mesh.GetName(), bone_name, bone_node )
						if bone_node in self.meshes:
							self.meshes.pop( self.meshes.index( bone_node ) )
							self.create_bone( bone_node, fbx_scene, coordinate_system_transform )

				# Make sure every bone is index'ed properly
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

					lmesh = mesh.GetNodeAttribute( )
					self.SetStatusText( 'Getting Mesh Data: {0}'.format( mesh.GetName( ) ) )
					mesh_data, vertices = get_mesh_data( lmesh, coordinate_system_transform )
					self.mesh_data.append( mesh_data )
					self.vertices.append( vertices )

					colliders = [ ] # TODO get colliders
					self.colliders.append( colliders )

					num_polygons = lmesh.GetPolygonCount( )
					num_polygon_verts = lmesh.GetPolygonVertexCount( )

					# get the vert/weight info
					self.SetStatusText( 'Getting Mesh Bone Weights: {0}'.format( mesh.GetName( ) ) )
					bone_weights, bones = get_boneweights( lmesh, vertices )

					# only add a mesh to the list if it has bones
					# we are only exporting character meshes at this time
					if bones:
						self.bone_weights.append( bone_weights )
						self.mesh_names.append( mesh.GetName() )
						self.SetStatusText( 'Get the bone order ...' )
						self.update_bone_attributes( self.bones, self.nodes )
						bone_order = self.get_bone_order( )
						self.bone_orders.append( bone_order )


				# get the materials
				for mesh in self.meshes:
					lmesh = mesh.GetNodeAttribute( )

					materials = get_fbx_materials( lmesh )
					mats = [ ]
					textures = [ ]
					mat_index = 0
					for material in materials:

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


	def create_tag( self, node, scene, coordinate_system_transform ):
		"""
		If the incoming node is a "tag", create a tag object for it

		*Arguments:*
			* ``node`` fbx node
			* ``scene`` fbx scene
			* ``coordinate_system_transform`` the transform we use to convert from fbx to game

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
		if node_is_tag or '$prop' in node.GetName():
			tag = Node_Tag( node, scene, coordinate_system_transform )
			self.tags.append( tag )


	def create_mesh( self, node, scene, coordinate_system_transform ):
		"""
		If the incoming node is a "mesh", create a mesh object for it

		*Arguments:*
			* ``node`` fbx node
			* ``scene`` fbx scene
			* ``coordinate_system_transform`` the transform we use to convert from fbx to game

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
		if node_is_bone:
			self.create_bone( node, scene, coordinate_system_transform )
		else:
			self.meshes.append( node )


	def create_bone( self, node, scene, coordinate_system_transform ):
		"""
		If the incoming node is a "bone", create a bone object for it

		*Arguments:*
			* ``node`` fbx node
			* ``scene`` fbx scene
			* ``coordinate_system_transform`` the transform we use to convert from fbx to game

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
			bone = Node_Bone( node, scene, coordinate_system_transform )
			self.bones.append( bone )


	def get_node_content( self, node, scene, coordinate_system_transform ):
		"""
		Determine the type of the incoming node and create a specific object that we will use later

		*Arguments:*
			* ``node`` fbx node
			* ``scene`` fbx scene
			* ``coordinate_system_transform`` the transform we use to convert from fbx to game

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
				self.create_bone( node, scene, coordinate_system_transform )

			elif node_attribute_type == FbxCommon.FbxNodeAttribute.eMesh:
				self.create_mesh( node, scene, coordinate_system_transform )

			elif node_attribute_type == FbxCommon.FbxNodeAttribute.eNull:
				self.create_tag( node, scene, coordinate_system_transform )

			else:
				print 'Node is not a type that we care about right now: {0}'.format( node.GetName( ) )
				pass


	def get_node_hierarchy( self, node, node_depth, scene, coordinate_system_transform ):
		"""
		Recursively get the heirarchy of objects from the FBX scene derived from the give root node, node

		*Arguments:*
			* ``node`` Current fbx scene root node
			* ``node_depth`` Depth of current node in the fbx scene
		* ``scene`` Fbx scene
		* ``coordinate_system_transform`` transform to convert fbx matrix to game matrix

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
		print 'Node: {0} NodeIndex: {1} Depth: {2}'.format( node.GetName(), self.node_index, node_depth )
		if node.GetParent( ):
			print '\tParent: {0}'.format( node.GetParent().GetName() )
		node_obj = Node_Info( node, self.node_index )
		self.nodes[ node ] = node_obj

		node_string = ""
		for i in range( node_depth ):
			node_string += "     "

		node_string += node.GetName( )
		if DEBUG_OUTPUT:
			print( node_string )
		self.get_node_content( node, scene, coordinate_system_transform )

		for i in range( node.GetChildCount( ) ):
			self.node_index += 1
			self.get_node_hierarchy( node.GetChild( i ), node_depth + 1, scene, coordinate_system_transform )



	def get_fbx_hierarchy( self, scene, coordinate_system_transform ):
		"""
		Get the heirarchy of objects from the FBX scene
		Starting with the scene root objects

		*Arguments:*
			* ``scene`` Fbx scene
			* ``coordinate_system_transform`` transform to convert fbx matrix to game matrix

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
			self.get_node_hierarchy( scene_root_node.GetChild( i ), 0, scene, coordinate_system_transform )
			self.node_index += 1


	def get_bone_order( self ):
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
				if DEBUG_OUTPUT:
					print 'Bone: {0} Order: {1}'.format( bone.name, bone.index )
				bone_order[ bone.index ] = bone

			if DEBUG_OUTPUT:
				print 'Sorted Bone Order Keys: {0}'.format( sorted( bone_order.keys( ) ) )

			order = 0
			for index in sorted( bone_order.keys( ) ):
				if DEBUG_OUTPUT:
					print ' Setting Bone: {0} Order: {1}'.format( bone_order[index].name, order )
				bone_order[index].index = order
				bone_order[index].id = order
				order += 1

			# update Tags parent index from this new order
			for tag in self.tags:
				if DEBUG_OUTPUT:
					print 'Tag: {0}'.format( tag.name )
				for index in sorted( bone_order.keys( ) ):
					# if the tag parent is the current bone set the index
					if tag.parent == bone_order[ index ].node:
						if DEBUG_OUTPUT:
							print '  Found Parent: {0}'.format( bone_order[ index ].name )
						tag.parent_index = bone_order[ index ].index
						break

			# update Bones parent index from this new order
			for bone in self.bones:
				for index in sorted( bone_order.keys( ) ):
					# if the bone parent is the current bone set the index
					if bone.node.GetParent() == bone_order[ index ].node:
						if DEBUG_OUTPUT:
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

		self.update_ui( )
		self.SetFocus( )


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

		# update the mesh names list
		if self.mesh_names:
			self.mesh_list.SetItems( self.mesh_names )
			self.mesh_list.SetSelection( 0 )
			self.selected_mesh = 0

		if not self.selected_mesh is None:

			# fill out the mesh info
			self.text_triangle_count.SetLabel( '  Triangles: {0}'.format( len( self.mesh_data[ self.selected_mesh ] ) ) )
			self.text_vertex_count.SetLabel( '  Vertices: {0}'.format( len( self.vertices[ self.selected_mesh ] ) ) )
			self.text_uv_count.SetLabel( '  UVs: {0}'.format( len( self.vertices[ self.selected_mesh ] ) ) )
			self.text_material_count.SetLabel( '  Materials: {0}'.format( len( self.materials[ self.selected_mesh ] ) ) )
			self.text_collider_count.SetLabel( '  Colliders: {0}'.format( len( self.colliders[ self.selected_mesh ] ) ) )
			self.text_bone_count.SetLabel( '  Bones: {0}'.format( len( self.bones ) ) )
			self.text_tag_count.SetLabel( '  Tags: {0}'.format( len( self.tags ) ) )
			self.fbx_text.SetValue( ' ' )
			self.rig_text.SetValue( '*.rigx' )
			self.cmesh_text.SetValue( '*.cmeshx' )
			self.matlib_text.SetValue( '*.matlibx' )

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
			self.fbx_text.SetValue( self.fbx_file )
			self.rig_text.SetValue( self.rigx_file )
			self.cmesh_text.SetValue( self.cmeshx_file )
			self.matlib_text.SetValue( self.matlibx_file )
		else:
			self.fbx_text.SetValue( ' ' )
			self.rig_text.SetValue( '*.rigx' )
			self.cmesh_text.SetValue( '*.cmeshx' )
			self.matlib_text.SetValue( '*.matlibx' )


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