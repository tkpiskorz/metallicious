path_to_mod_seminario = "/u/fd/chem1540/github/ModSeminario_Py/Python_Modified_Seminario_Method"

import autode as ade
#method = ade.methods.XTB()
import os
import re
from subprocess import Popen, DEVNULL
import numpy as np

from MDAnalysis.lib.distances import calc_dihedrals
import MDAnalysis

method = ade.methods.ORCA()

try:
    from data import name_to_atomic_number
    from improper_torsion import find_dihedrals_and_values
except:
    from cgbind2pmd.data import name_to_atomic_number
    from cgbind2pmd.improper_torsion import find_dihedrals_and_values

def orca_to_fchk(filename="site_opt_orca.hess", output_fchk="lig.fchk"):
    File = open(filename)
    text = File.read()
    File.close()

    temp = text[text.find('$atoms'):text.find("$actual_temperature")]
    N_atoms = int(temp.splitlines()[1])

    gaussian_coord_string = ''
    gaussian_atomic_number_string = ''

    c = 0
    d = 0
    for line in temp.splitlines()[2:]:
        print(line)

        if len(line.split()) > 0:
            for a in [2, 3, 4]:

                gaussian_coord_string += f" {float(line.split()[a]): .8e}"
                c += 1
                if c % 5 == 0:
                    gaussian_coord_string += '\n'
                    c = 0
            gaussian_atomic_number_string += f" {name_to_atomic_number[line.split()[0].title()]: 11d}"
            d += 1

            if d % 5 == 0:
                gaussian_atomic_number_string += '\n'
                d = 0

    temp = text[text.find('$hessian'):text.find("$vibrational_frequencies")]
    N = int(temp.splitlines()[1])

    hess_string = ['' for a in range(N)]

    #for a in range(int(N / 5) + 1):
    for a in range(int(N / 5)):
        temp2 = temp.splitlines()[3 + (1 + N) * (a):2 + (1 + N) * (a + 1)]
        for b in range(N):
            hess_string[b] += temp2[b][6:]

    gaussian_hess_string = ''

    c = 0
    for a in range(N):
        for b in range(a + 1):
            gaussian_hess_string += f" {float(hess_string[b].split()[a]): .8e}"
            c += 1
            if c % 5 == 0:
                gaussian_hess_string += '\n'
                c = 0

    File = open(output_fchk, "w")
    print(f"Atomic numbers                             I   N={N_atoms:12d}", file=File)
    print(gaussian_atomic_number_string, file=File)
    print("Nuclear charges        \n", file=File)
    print(f"Current cartesian coordinates              R   N={N:12d}", file=File)
    print(gaussian_coord_string, file=File)
    print("Force Field            \n", file=File)
    print(f"Cartesian Force Constants                  R   N={N:12d}", file=File)
    print(gaussian_hess_string, file=File)
    print("Dipole Moment          \n", file=File)
    File.close()


def orca_to_log(filename="site_opt_orca.out", log_output="lig.log"):
    File = open(filename)
    text = File.read()
    File.close()

    start_line = text.find("        Definition                    Value    dE/dq     Step     New-Value")
    n_bonds = 1
    n_angles = 1

    File = open(log_output, "w")

    print(" --------------------------                            --------------------------", file=File)
    print(" ! Name  Definition              Value          Derivative Info.                !", file=File)
    print(" --------------------------------------------------------------------------------", file=File)

    for line in text[start_line:].splitlines()[2:]:
        if line == "    ----------------------------------------------------------------------------":
            break

        if line[8] == 'B':

            match = re.search("\([a-zA-Z]+\s*(\d+),[a-zA-Z]+\s*(\d+)\)", line)
            idx1 = int(match.group(1)) + 1
            idx2 = int(match.group(2)) + 1

            number_of_spaces = 22 - len(f"R({idx1:d},{idx2:d})")
            value = float(line[line.find(")"):].split()[1])

            print(
                f" ! R{n_bonds:<4d} R({idx1:d},{idx2:d}){number_of_spaces * ' ':s}{0.0: 8.4f}         -DE/DX =    0.0                 !",
                file=File)
            n_bonds += 1

        elif line[8] == 'A':
            match = re.search("A\([a-zA-Z]+\s*(\d+),[a-zA-Z]+\s*(\d+),[a-zA-Z]+\s*(\d+)\)", line)
            idx1 = int(match.group(1)) + 1
            idx2 = int(match.group(2)) + 1
            idx3 = int(match.group(3)) + 1

            number_of_spaces = 22 - len(f"A({idx1:d},{idx2:d},{idx3:d})")

            value = float(line[line.find(")"):].split()[1])

            print(
                f" ! A{n_angles:<4d} A({idx1:d},{idx2:d},{idx3:d}){number_of_spaces * ' ':s}{value:8.4f}         -DE/DX =    0.0                 !",
                file=File)

            n_angles += 1
    print(" ! D1    D(1,2,3,4)              0.0000         -DE/DX =    0.0                 !", file=File)
    print(" --------------------------------------------------------------------------------\n", file=File)
    File.close()

def strip_numbers_from_atom_name(atom_name):
    return re.match("([a-zA-Z]+)", atom_name).group(0)

def read_bonds():
    File = open("Modified_Seminario_Bonds")
    text = File.read()
    File.close()
    bonds = {}
    for line in text.splitlines():
        striped_bond = [strip_numbers_from_atom_name(name).title() for name in line.split()[0].split('-')]
        unsorted_bond = (int(line.split()[3]) - 1, int(line.split()[4]) - 1)
        argsorted = np.argsort(unsorted_bond)

        bonds[tuple(np.sort(unsorted_bond)), (striped_bond[argsorted[0]], striped_bond[argsorted[1]])] = (
            float(line.split()[2]), float(line.split()[1]))
    return bonds

def remove_non_metal_donor_bonds(bonds, metal_name, donors=['N', 'O', 'S']):
    metal_name = metal_name.title()
    new_bonds = {}
    for bond in bonds:
        if metal_name.title() in bond[1]:
            if (bond[1][0] == metal_name and bond[1][1] in donors) or (
                    bond[1][1] == metal_name and bond[1][0] in donors):
                new_bonds[bond[0]] = bonds[bond]
            else:
                print("Not coping, metal connected not to the donor")
                print(bond[1])
        else:
            new_bonds[bond[0]] = bonds[bond]
    return new_bonds

def read_and_symmetrize_bonds(bonds, metal_name, starting_index, indecies, unique_ligands_pattern, donors=["N", "O", "S"]):

    metal_index = 0  # TODO metal again first
    for unique_ligand in list(set(unique_ligands_pattern)):
        unique_ligand_indecies = [a for a, b in enumerate(unique_ligands_pattern) if b == unique_ligand]
        print(unique_ligand_indecies)
        index_select = np.array(starting_index)[np.array(unique_ligand_indecies) + 1]
        index_distance = index_select - index_select[0]
        print(index_distance)

        for atom_indeces in (indecies[unique_ligand + 1]):
            for bond in bonds:
                if atom_indeces in bond:
                    if metal_index not in bond:
                        length = 0
                        k = 0
                        for distance in index_distance:
                            temp = bonds[bond[0] + distance, bond[1] + distance]
                            length += temp[0]
                            k += temp[1]

                        length /= len(index_distance)
                        k /= len(index_distance)

                        for distance in index_distance:
                            bonds[bond[0] + distance, bond[1] + distance] = (np.round(length, 3), np.round(k, 3))
                    else:
                        length = 0
                        k = 0
                        for distance in index_distance:
                            temp = bonds[bond[0], bond[1] + distance]
                            length += temp[0]
                            k += temp[1]

                        length /= len(index_distance)
                        k /= len(index_distance)

                        for distance in index_distance:
                            bonds[bond[0], bond[1] + distance] = (np.round(length, 3), np.round(k, 3))
    return bonds

def bond_remove_invalid_and_symmetrize(bonds_with_names, metal_name, starting_index, indecies, unique_ligands_pattern, donors=["N", "O", "S"]):
    bonds = remove_non_metal_donor_bonds(bonds_with_names, metal_name, donors=donors)
    bonds = read_and_symmetrize_bonds(bonds, metal_name, starting_index, indecies, unique_ligands_pattern,
                              donors=donors)
    return bonds



def read_angles():
    File = open("Modified_Seminario_Angle")
    text = File.read()
    File.close()

    angles = {}
    for line in text.splitlines():
        names = [strip_numbers_from_atom_name(name).title() for name in line.split()[0].split('-')]
        indecies = [int(line.split()[3]) - 1, int(line.split()[4]) - 1, int(line.split()[5]) - 1]

        if indecies[0] < indecies[2]:  # we have indecies from smaler to larger in the angles
            angles[tuple(indecies), tuple(names)] = (float(line.split()[2]), float(line.split()[1]))
        else:
            angles[tuple(indecies[::-1]), tuple(names[::-1])] = (float(line.split()[2]), float(line.split()[1]))
    return angles


def remove_non_metal_donor_bonds(angles, metal_name, donors=['N', 'S', 'O']):
    metal_name = metal_name.title()
    new_angles = {}
    for angle in angles:
        if metal_name in angle[1]:
            metal_on_side_condition = (
                        (angle[1][0] == metal_name or angle[1][2] == metal_name) and (angle[1][1] in donors))
            metal_in_middle_condition = (
                        angle[1][1] == metal_name and (angle[1][0] in donors) and (angle[1][2] in donors))

            if metal_on_side_condition or metal_in_middle_condition:
                new_angles[angle[0]] = angles[angle]
            else:
                print("Not valid bond, metal-metal not included (yet)")
        else:
            new_angles[angle[0]] = angles[angle]
    return new_angles


#(metal_name, starting_index, indecies, unique_ligands_pattern, donors = ["N", "O"])
def symmetrize_angles(angles, metal_name, starting_index, indecies, unique_ligands_pattern):
    metal_index = 0

    for unique_ligand in list(set(unique_ligands_pattern)):
        unique_ligand_indecies = [a for a, b in enumerate(unique_ligands_pattern) if b == unique_ligand]
        print(unique_ligand_indecies)
        index_select = np.array(starting_index)[np.array(unique_ligand_indecies) + 1]
        index_distance = index_select - index_select[0]
        print(index_distance)
        for atom_indeces in (indecies[unique_ligand + 1]):
            # print(atom_indeces)
            for angle in angles:
                if atom_indeces in angle:
                    metal0 = 1
                    metal2 = 1

                    if metal_index == angle[0]:
                        metal0 = 0
                    elif metal_index == angle[1]:
                        metal2 = 0

                    if not metal_index == angle[1]:

                        length = 0
                        k = 0
                        for distance in index_distance:
                            temp = angles[angle[0] + distance * metal0, angle[1] + distance, angle[2] + distance * metal2]
                            length += temp[0]
                            k += temp[1]

                        length /= len(index_distance)
                        k /= len(index_distance)

                        for distance in index_distance:
                            angles[angle[0] + distance * metal0, angle[1] + distance, angle[2] + distance * metal2] = (
                            np.round(length, 3), np.round(k, 3))

                    elif angle[1] == metal_index:
                        # There is no simple way of symmetrizing this interaction, e.g. PdL4, some are orineted 90 deg some 180 deg
                        None
    return angles

def read_and_symmetrize_angles(metal_name, starting_index, indecies, unique_ligands_pattern, donors=["N", "O", 'S']):
    angles = read_angles()
    angles = remove_non_metal_donor_bonds(angles, metal_name, donors=donors)
    angles = symmetrize_angles(angles, metal_name, starting_index, indecies, unique_ligands_pattern)
    return angles


def angle_remove_invalid_and_symmetrize(angles_with_names, metal_name, starting_index, indecies, unique_ligands_pattern,
                                       donors=["N", "O", "S"]):
    angles = remove_non_metal_donor_bonds(angles_with_names, metal_name, donors=donors)
    angles = symmetrize_angles(angles, metal_name, starting_index, indecies, unique_ligands_pattern)
    return angles


def extend_angle_to_dihedral(angle, bonds):
    dihedrals = []
    last_atom = angle[-1]
    temp = list(set(np.concatenate([[bond[0], bond[1]] for bond in bonds if last_atom in bond])))
    temp.remove(last_atom)
    for a in temp:
        if a not in angle:
            dihedrals.append(angle + [a])

    last_atom = angle[0]
    temp = list(set(np.concatenate([[bond[0], bond[1]] for bond in bonds if last_atom in bond])))
    temp.remove(last_atom)
    for a in temp:
        if a not in angle:
            dihedrals.append([a] + angle)
    return dihedrals

def generate_all_dihedrals(angles, bonds, metal_index=0):
    dihedrals = []
    for angle_indexes in angles:
        if metal_index in angle_indexes:
            extended_dihedrals = extend_angle_to_dihedral(list(angle_indexes), bonds)
            dihedrals += extended_dihedrals

    # remove double counted dihedrals:
    new_dihedrals = []
    for a, dihedral in enumerate(dihedrals):
        if dihedral not in new_dihedrals and dihedral[::-1] not in new_dihedrals:
            new_dihedrals.append(dihedral)
    return new_dihedrals

def create_dummy_dihedrals(angles, bonds, filename, metal_index=0):  # TODO check metal index
    syst_opt = MDAnalysis.Universe(filename)
    dihedrals_indexes = generate_all_dihedrals(angles, bonds, metal_index)
    dihedrals = {}
    for dihedral in dihedrals_indexes:
        dihedrals[tuple(dihedral)] = (np.rad2deg(calc_dihedrals(*syst_opt.atoms[dihedral].positions)), 0)
    return dihedrals

# TODO there is something wierd about the angles, they do not much with Merz, I might solve this by accident

def strip_names_from_covalent(covalent_paramters):
    new_covalent = {}
    for covalent in covalent_paramters:
        new_covalent[covalent[0]] = covalent_paramters[covalent]
    return new_covalent


def frequencies(filename, charge = 0, keywords=['PBE0', 'D3BJ', 'def2-SVP', 'tightOPT', 'freq'], mult=1):
    print("AAA")
    print(method)
    site = ade.Molecule(filename, charge=charge, mult=mult)
    site.optimise(method=method, keywords=keywords)
    return site.name

def simple_seminario(filename, keywords=['PBE0', 'D3BJ', 'def2-SVP', 'tightOPT', 'freq'], charge=0, mult=1):

    here = os.getcwd()
    os.system("mkdir bonded")
    os.chdir("bonded")

    print("Optimising, parameters:", filename)

    name = frequencies("../"+filename, charge, keywords=keywords, mult=mult)
    orca_to_fchk(f"{name:s}_opt_orca.hess")
    orca_to_log(f"{name:s}_opt_orca.out")

    os.chdir(path_to_mod_seminario) #TODO this can be done form just python scrpit
    command = f'python modified_Seminario_method.py {here:s}/bonded/ {here:s}/bonded/ 1.000' #TODO modify the 1.000 modifier
    process = Popen(command.split(), stdout=DEVNULL, stderr=DEVNULL)
    process.wait()
    os.chdir(here+"/bonded")

    bonds_with_names = read_bonds()
    angles_with_names = read_angles()

    dummy_dihedrals = create_dummy_dihedrals(strip_names_from_covalent(angles_with_names), strip_names_from_covalent(bonds_with_names), filename=f"{name:s}_opt_orca.xyz")



    os.chdir(here)

    return bonds_with_names, angles_with_names, dummy_dihedrals


def single_seminario(filename, metal_charge, metal_name, starting_index, indecies, unique_ligands_pattern, keywords=['PBE0', 'D3BJ', 'def2-SVP', 'tightOPT', 'freq'], mult=1, improper_metal = False, donors=['N', 'S', 'O']):
    bonds_with_names, angles_with_names, dummy_dihedrals = simple_seminario(filename, keywords=keywords, charge=metal_charge, mult=mult) # what about ligand charge!!!! # TODO

    if improper_metal:
        improper_dihedrals = find_dihedrals_and_values(bonds_with_names, metal_name, unique_ligands_pattern, starting_index, indecies, charge=metal_charge)
        dihedrals = {**dummy_dihedrals, **improper_dihedrals}
    else:
        dihedrals = dummy_dihedrals

    bonds = bond_remove_invalid_and_symmetrize(bonds_with_names, metal_name, starting_index, indecies, unique_ligands_pattern,
                                       donors=donors)

    angles = angle_remove_invalid_and_symmetrize(angles_with_names, metal_name, starting_index, indecies, unique_ligands_pattern,
                                       donors=donors)
    if improper_metal:
        None

    return bonds, angles, dihedrals

def multi_seminario(metal_charge, metal_name, keywords=['PBE0', 'D3BJ', 'def2-SVP', 'tightOPT', 'freq'], mult=1, improper_metal=False, donors=['N', 'S', 'O']):

    File = open("INFO.dat")
    text = File.read()
    File.close()

    n_sites = text.count("ligand_pattern")
    print("Number of sites", n_sites)

    print("Autode:", ade.__version__)

    n_site = 0
    bondss = []
    angless = []
    dihedralss = []

    for line in text.splitlines():
        if "ligand_pattern:" in line:
            unique_ligands_pattern = list(map(int, line[15:].split(',')))

        if "starting_index:" in line:
            starting_index = list(map(int, line[15:].split(',')))
            indecies = [list(range(starting_index[a - 1], starting_index[a])) for a in range(1, len(starting_index))]

            bonds, angles, dihedrals = single_seminario(f"site{n_site:d}.xyz", metal_charge, metal_name, starting_index, indecies, unique_ligands_pattern, keywords=keywords, mult=mult, improper_metal=improper_metal, donors=donors)

            print(dihedrals)

            File = open(f"bonds_{n_site:d}.dat", "w")
            for bond in bonds:
                File.write(f'{"-".join(list(map(str, bond))):}:{",".join(list(map(str, bonds[bond]))):}')
            File.close()
            bondss.append(bonds)

            File = open(f"angles_{n_site:d}.dat", "w")
            for angle in angles:
                File.write(f'{"-".join(list(map(str, angle))):}:{",".join(list(map(str, angles[angle]))):}')
            File.close()
            angless.append(angles)

            File = open(f"dihedrals_{n_site:d}.dat", "w")
            for dihedral in dihedrals:
                File.write(f'{"-".join(list(map(str, dihedral))):}:{",".join(list(map(str, dihedrals[dihedral]))):}')
            File.close()
            dihedralss.append(dihedrals)

    return (bondss, angless, dihedralss)

import argparse

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-metal_charge", help="Clean structure")
    parser.add_argument("-metal_name", help="Clean structure")
    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()
    multi_seminario(args.metal_charge, args.metal_name)







