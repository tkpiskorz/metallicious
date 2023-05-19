import os
import parmed as pmd
import MDAnalysis
import numpy as np
import networkx as nx

from MDAnalysis.lib.distances import distance_array

try:
    from cgbind2pmd.extract_metal_site import find_bound_ligands_nx
    from cgbind2pmd.log import logger
    from cgbind2pmd.mapping import map_two_structures

except:
    from extract_metal_site import find_bound_ligands_nx
    from log import logger
    from mapping import map_two_structures

def load_fingerprint_from_file(name_of_binding_side, fingerprint_style='full'):
    '''
    Loads topology and coordinates of the fingerprint. If fingerprint not "full", then it will be trunked to the specified fingerprint style:
    - dihdral (or dih) - truncated to atoms within 3 bond length from metal
    - angle (or ang) - truncated to atoms within 2 bond length from metal
    - bond - truncated to atoms within 1 bond length from metal

    :param name_of_binding_side:
    :param fingerprint_style:
    :return:
    '''

    topol = pmd.load_file(f'{os.path.dirname(__file__):s}/library/{name_of_binding_side:s}.top')
    syst_fingerprint = MDAnalysis.Universe(f"{os.path.dirname(__file__):s}/library/{name_of_binding_side:s}.pdb")

    if fingerprint_style=='full':
        # do not truncate
        return topol, syst_fingerprint

    elif fingerprint_style in ['dihedral', 'dih', 'angle', 'ang', 'bond']:
        metal_topology = topol.atoms[0]  # As it is now, the topologies are save with first atom as metal

        if fingerprint_style == 'dihedral' or fingerprint_style == 'dih':
            atoms_bound_to_metal_by_bonded = list(set(
                np.concatenate([[angle.atom1.idx, angle.atom2.idx, angle.atom3.idx, angle.atom4.idx] for angle in
                                metal_topology.dihedrals])))
        elif fingerprint_style == 'angle' or fingerprint_style == 'ang':
            atoms_bound_to_metal_by_bonded = list(set(
                np.concatenate(
                    [[angle.atom1.idx, angle.atom2.idx, angle.atom3.idx] for angle in metal_topology.angles])))
        elif fingerprint_style == 'bond':
            atoms_bound_to_metal_by_bonded = list(
                set(np.concatenate([[bond.atom1.idx, bond.atom2.idx] for bond in metal_topology.bonds])))

        atoms_to_strip = []
        residual_charge = 0.0
        for atom in topol.atoms:
            if atom.idx not in atoms_bound_to_metal_by_bonded:
                atoms_to_strip.append(atom.idx)
                residual_charge += atom.charge

        residual_charge /= len(atoms_bound_to_metal_by_bonded)

        for idx in atoms_bound_to_metal_by_bonded:
            topol.atoms[idx].charge += residual_charge


        topol.strip(f"@{','.join(list(map(str, np.array(atoms_to_strip) + 1))):s}")
        new_syst_fingerprint = syst_fingerprint.select_atoms(
            f"not index {' '.join(list(map(str, np.array(atoms_to_strip)))):s}")
        new_syst_fingerprint.write("temp.pdb")
        new_syst_fingerprint = MDAnalysis.Universe("temp.pdb")

        return topol, new_syst_fingerprint.atoms

        '''
        elif fingerprint_style=='angle' or fingerprint_style=='ang':
            metal_topology = topol.atoms[0]
    
            atoms_bound_to_metal_by_angle = list(set(
                np.concatenate([[angle.atom1.idx, angle.atom2.idx, angle.atom3.idx] for angle in metal_topology.angles])))
            #atoms_bound_to_metal_by_bond = list(
            #    set(np.concatenate([[bond.atom1.idx, bond.atom2.idx] for bond in metal_topology.bonds])))
    
            atoms_to_strip = []
            residual_charge = 0.0
            for atom in topol.atoms:
                if atom.idx not in atoms_bound_to_metal_by_angle:
                    atoms_to_strip.append(atom.idx)
                    residual_charge += atom.charge
    
    
            residual_charge /= len(atoms_bound_to_metal_by_angle)
    
            #residual_charge = 0.0
            #for atom in topol.atoms:
            #    if atom.idx not in atoms_bound_to_metal_by_bond:
            #        residual_charge += atom.charge
            #residual_charge /= len(atoms_bound_to_metal_by_bond)
    
            for idx in atoms_bound_to_metal_by_angle:
                    #if idx in atoms_bound_to_metal_by_bond:
                    topol.atoms[idx].charge += residual_charge
                    #else:
                    #topol.atoms[idx].charge = 0.0
    
            topol.strip(f"@{','.join(list(map(str, np.array(atoms_to_strip) + 1))):s}")
            new_syst_fingerprint = syst_fingerprint.select_atoms(f"not index {' '.join(list(map(str, np.array(atoms_to_strip)))):s}")
            new_syst_fingerprint.write("temp.pdb")
            print(os.getcwd())
            new_syst_fingerprint = MDAnalysis.Universe("temp.pdb")
            return topol, new_syst_fingerprint.atoms
    
        elif fingerprint_style=='bond':
            metal_topology = topol.atoms[0]
            atoms_bound_to_metal_by_bond = list(
                set(np.concatenate([[bond.atom1.idx, bond.atom2.idx] for bond in metal_topology.bonds])))
            atoms_to_strip = []
    
            residual_charge = 0.0
            for atom in topol.atoms:
                if atom.idx not in atoms_bound_to_metal_by_bond:
                    atoms_to_strip.append(atom.idx)
                    residual_charge += atom.charge
    
            #topol.atoms[0].charge = residual_charge
            residual_charge /= len(atoms_bound_to_metal_by_bond)
    
    
            for idx in atoms_bound_to_metal_by_bond:
                    #if idx in atoms_bound_to_metal_by_bond:
                    topol.atoms[idx].charge += residual_charge
                    #else:
                    #topol.atoms[idx].charge = 0.0
    
            #for atom in topol.atoms:
            #    atom.charge = 0.0
    
            topol.strip(f"@{','.join(list(map(str, np.array(atoms_to_strip) + 1))):s}")
            new_syst_fingerprint = syst_fingerprint.select_atoms(f"not index {' '.join(list(map(str, np.array(atoms_to_strip)))):s}")
            new_syst_fingerprint.write("temp.pdb") #TODO this probably can be rediex in a nicer way...
            new_syst_fingerprint = MDAnalysis.Universe("temp.pdb")
            return topol, new_syst_fingerprint.atoms
        '''

    else:
        raise

from rdkit import Chem
def reduce_site_to_fingerprint(cage_filename, metal_index, syst_fingerprint, cutoff=9, guessing=False):

    cage = MDAnalysis.Universe(cage_filename)
    # def strip_numbers_from_atom_name(atom_name):
    #    return re.match("([a-zA-Z]+)", atom_name).group(0)

    # metal_name=strip_numbers_from_atom_name(syst_fingerprint.atoms[metal_index].name)

    # metal_type = syst_fingerprint.select_atoms(f'index {metal_index:}').atoms[0].type

    syst_fingerprint_no_metal = syst_fingerprint.atoms[1:]


    bonds = MDAnalysis.topology.guessers.guess_bonds(syst_fingerprint_no_metal.atoms,
                                                     syst_fingerprint_no_metal.atoms.positions)
    G_fingerprint = nx.Graph()

    if len(bonds) > 0:  # fingerprint with ligands larger then one atom
        G_fingerprint = nx.Graph(bonds)
    elif len(bonds) == 0:  # not bonds, this has to be minimal fingerprint, only donor atoms
        G_fingerprint.add_nodes_from(syst_fingerprint_no_metal.atoms.indices)

    nx.set_node_attributes(G_fingerprint, {atom.index: atom.name[0] for atom in syst_fingerprint_no_metal.atoms},
                           "name")
    G_fingerprint_subs = [G_fingerprint.subgraph(a) for a in nx.connected_components(G_fingerprint)]

    logger.info(f"     [ ] Mapping fingerprint to metal center: {metal_index:d}")
    '''
    cut_sphere = self.cage.select_atoms(f'index {metal_index:d} or around {cutoff:f} index {metal_index:d}')
    G_cage = nx.Graph(MDAnalysis.topology.guessers.guess_bonds(cut_sphere.atoms, cut_sphere.atoms.positions))
    nx.set_node_attributes(G_cage, {atom.index: atom.name[0] for atom in cut_sphere.atoms}, "name")
    G_sub_cages = [G_cage.subgraph(a) for a in nx.connected_components(G_cage)]
    G_sub_cages = sorted(G_sub_cages, key=len, reverse=True) # we assume that the largerst group are  ligands, is this reasonable? TODO
    '''

    G_sub_cages, closest_atoms = find_bound_ligands_nx(cage, metal_index, cutoff=cutoff)
    closest_atoms = np.concatenate(closest_atoms)

    number_ligands_bound = len(G_sub_cages)
    logger.info(f"         Number of ligands bound to metal: {number_ligands_bound:d}")

    if len(G_sub_cages) != len(G_fingerprint_subs) and guessing:
        logger.info(f"[!] Not the same number of sites {guessing:}")
        return False
    elif len(G_sub_cages) != len(G_fingerprint_subs) and not guessing:
        logger.info(
            f"[!] Not the same number of sites {len(G_sub_cages):}!={len(G_fingerprint_subs):} guessing={guessing:}")
        raise

    selected_atoms = []
    end_atoms = []

    for G_sub_cage in G_sub_cages:
        largest_common_subgraph = []
        finerprint_idx = None
        trial = 0
        for G_idx, G_fingerprint_sub in enumerate(G_fingerprint_subs):

            # ISMAGS is a slow algorithm, so we want to makes sure that we match correct substructure, we make simple assesments:
            # Let's try to use rdkit:

            cage.select_atoms(
                f'index {" ".join(list(map(str, list(G_sub_cage)))):s}').write('mol1.pdb')

            syst_fingerprint_no_metal.select_atoms(
                f'index {" ".join(list(map(str, list(G_fingerprint_sub)))):s}').write('mol2.pdb')
            cage_sub_rdkit = Chem.MolFromPDBFile("mol1.pdb")
            fp_sub_rdkit = Chem.MolFromPDBFile("mol2.pdb")

            passed_conditions = cage_sub_rdkit.HasSubstructMatch(fp_sub_rdkit)

            '''
            # ISMAGS is a slow algorithm, so we want to makes sure that we match correct substructure, we make simple assesments:
            # 1) Mismatch of size, i.e., fingerprint is larger then ligand
            if len(G_fingerprint_sub) <= len(G_sub_cage):

                # 2) Fingerprint has more rings than the ligand
                rings_sub_cage = nx.cycle_basis(G_sub_cage)
                rings_sub_fp = nx.cycle_basis(G_fingerprint_sub)

                passed_conditions=False
                if len(rings_sub_fp) == len(rings_sub_cage):
                    # If fingering has the same number of rings we can check the sidechans, otherwise we have to go with ISMAGS
                    # becasue fingerprint can be just cutted ring, [we could go with all permutation of rings, but might be too complex)


                    # 3) Fingerprint has (a) more sidechains than the ligand, and they are (b) longer than ligand
                    sidechains_nodes_sub_cage = [node for node in G_sub_cage.nodes if node not in np.concatenate(rings_sub_cage)]
                    sidechains_sub_cage = np.sort([len(G_sidechain_sub) for G_sidechain_sub in
                     nx.connected_components(G_sub_cage.subgraph(sidechains_nodes_sub_cage))])

                    sidechains_nodes_sub_fp = [node for node in G_fingerprint_sub.nodes if node not in np.concatenate(rings_sub_fp)]
                    sidechains_sub_fp = np.sort([len(G_sidechain_sub) for G_sidechain_sub in
                                           nx.connected_components(G_fingerprint_sub.subgraph(sidechains_nodes_sub_fp))])

                    if len(sidechains_sub_fp) <= len(sidechains_sub_cage): # condition (a)
                        if (sidechains_sub_cage[-len(sidechains_sub_fp):] - sidechains_sub_fp[:] >= 0).all(): # condition (b)
                            passed_conditions =True
                        #else:
                        #    print("Mismatch by size of sidechains")
                    #else:
                    #    print("Mismatch by number of sidechains")

                elif len(rings_sub_fp) < len(rings_sub_cage):
                    passed_conditions = True
                #else:
                #    print("Mismatch by rings")
            '''
            if passed_conditions:
                            ismags = nx.isomorphism.ISMAGS(G_sub_cage, G_fingerprint_sub,
                                                           node_match=lambda n1, n2: n1['name'] == n2['name'])

                            # largest_common_subgraph_nx = ismags.largest_common_subgraph()

                            # There can be many possibilities of isomorphism, not only due to the symmetry, but sometimes becasue
                            # ligand has more sites. In such case we need to make sure that closest to the metal atoms ("donors")
                            # are included

                            # logger.info(f'{ismags.largest_common_subgraph():}')
                            # This takes forever: # and should be removed in future generations:
                            #logger.info(
                            #    f"There are {len(list(ismags.largest_common_subgraph(symmetry=False))):} matching patterns")  # remove this

                            for largest_common_subgraph_iter in ismags.largest_common_subgraph(symmetry=False):
                                if len(largest_common_subgraph_iter) < len(G_fingerprint_sub):
                                    # we iterating through largest subgraph (so they have the same size). If one is smaller then the fingerprint
                                    # none will be larger and we should stop the loop
                                    break

                                #logger.info(
                                #    f'Iterating {largest_common_subgraph_iter:}, the size: {len(largest_common_subgraph_iter):}')
                                is_donor_included = [closest_atom in largest_common_subgraph_iter for closest_atom in
                                                     closest_atoms]

                                if any(is_donor_included):
                                    if len(largest_common_subgraph_iter) > len(largest_common_subgraph):
                                        largest_common_subgraph = largest_common_subgraph_iter
                                        finerprint_idx = G_idx
                                        #logger.info(f"Found pattern which has all donor atoms {largest_common_subgraph:}")
                                        break

            #else:
            #    print("Mismatch by size")
            #else:
            if finerprint_idx is None:
                trial += 1
                # we make sure that we find the maching ligannd

                if trial == len(G_fingerprint_sub):
                    if guessing:
                        return False
                    else:
                        assert trial < len(G_fingerprint_sub)

        if guessing:  # if we want to guess site, that might be not fulfiled, and that means it is not the corret site
            if len(largest_common_subgraph) == 0:
                return False
            elif not len(G_fingerprint_subs[finerprint_idx]) == len(largest_common_subgraph):
                return False
        else:
            # Check if the subgraph is the same size as fingerprint,
            #print(largest_common_subgraph)
            #if len(largest_common_subgraph) > 0:
            #    print("aaa")
            #if len(G_fingerprint_subs[finerprint_idx]) == len(largest_common_subgraph):
            #    print("bbb")

            assert len(largest_common_subgraph)>0
            assert len(G_fingerprint_subs[0]) == len(largest_common_subgraph)

        selected_atoms += largest_common_subgraph.keys()

        # Let's find the end atoms, they have diffrent degree: in cage they are connected, in the template not
        G_sub_cage_degree = G_sub_cage.degree
        G_fingerprint_subs_degree = G_fingerprint_subs[finerprint_idx].degree

        # We cut the last atom
        for key in largest_common_subgraph:
            if G_sub_cage_degree[key] != G_fingerprint_subs_degree[largest_common_subgraph[key]]:
                end_atoms.append(key)


    connected_cut_system = cage.select_atoms(f"index {metal_index:}") + cage.select_atoms(f"index {' '.join(map(str, selected_atoms)):}")

    return connected_cut_system, end_atoms


def find_mapping_of_fingerprint_on_metal_and_its_surroundings(cage_filename, metal_index,metal_name, syst_fingerprint, cutoff=9, guessing=False):
    result = reduce_site_to_fingerprint(cage_filename, metal_index, syst_fingerprint, cutoff=cutoff, guessing=guessing)

    if result: # the results are legit, we take them as input
        connected_cut_system, end_atoms = result
        print("Mapping: end atoms", end_atoms)
        # TODO I THINK that I used "end atoms" becasue of the charge , and that I did not want to coppy the aromatic to something bond (but then I should have just cat that atom in template (?)
        # TODO this is not good that I do not remember this choice
        #best_mapping, best_rmsd = map_two_structures(metal_index, connected_cut_system, syst_fingerprint, metal_name=self.metal_name, end_atoms=end_atoms)
        best_mapping, best_rmsd = map_two_structures(metal_index, connected_cut_system, syst_fingerprint, metal_name=metal_name)

        #def map_two_structures(self, connected_cut_system, metal_index, syst_fingerprint, cutoff=9, guessing=False):
        #def map_two_structures(self, connected_cut_system, metal_index, syst_fingerprint, end_atoms=[]):


    else: #we are guessing, and we missed
        return None, 1e10
    return best_mapping, best_rmsd



def guess_fingerprint(cage_filename, metal_index, metal_name = None, fingerprint_guess_list = None, m_m_cutoff=10): # TODO guessing is not working
    '''
    Tries to guess the fingerprint but itereting through the library and find lowest rmsd.
    :return:
    '''

    # Check avaialble sites in the library directory
    all_finerprints_names = []
    for file in os.listdir(f"{os.path.dirname(__file__):s}/library"):
        if file.endswith('.pdb'):
            all_finerprints_names.append(file[:-4])

    # We choose only the one which have the same name
    finerprints_names = []
    if fingerprint_guess_list is not None:
        for name in fingerprint_guess_list:
            if name not in all_finerprints_names:
                print("Fingerprint not available")
                raise
            else:
                finerprints_names.append(name)
    else:
        for name in all_finerprints_names:
            if metal_name.title() in name:
                finerprints_names.append(name)



    logger.info(f"Trying to guess which site it is: {finerprints_names:}")
    rmsd_best = 1e10
    name_of_binding_side = None
    for finerprint_name in finerprints_names:
        logger.info(f"[ ] Guessing fingerprint {finerprint_name:s}")
        syst_fingerprint = MDAnalysis.Universe(f"{os.path.dirname(__file__):s}/library/{finerprint_name:s}.pdb")
        # we need to find what is smaller

        metal_position = syst_fingerprint.atoms[0].position
        nometal_position = syst_fingerprint.atoms[1:].positions
        cutoff = np.min([np.max(distance_array(metal_position, nometal_position))+2.0, m_m_cutoff])
        #cutoff = 0.5*(cutoff+self.m_m_cutoff) # we make it 75% close to metal

        mapping_fp_to_new, rmsd = find_mapping_of_fingerprint_on_metal_and_its_surroundings(cage_filename, metal_index, metal_name, syst_fingerprint, guessing=True, cutoff=cutoff)


        if rmsd < rmsd_best:
            rmsd_best = rmsd
            name_of_binding_side = finerprint_name
            #self.ligand_cutoff = cutoff
        logger.info(f"    [ ] RMSD {rmsd:f}")

    logger.info(f"[+] Best fingerprint {name_of_binding_side:s} rmsd: {rmsd_best:f}")
    if rmsd_best > 1.0:
        logger.info("[!] Rmsd is quite large, want to proceed?") #TODO
    return name_of_binding_side

#TODO assert rediculsy small ligands
