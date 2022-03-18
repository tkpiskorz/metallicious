import parmed as pmd

from tempfile import mkdtemp
import os
import shutil
from subprocess import Popen, DEVNULL
from cgbind2pmd.log import logger

import numpy as np

def antechamber(pdbfile, charge, output, verbose=False):

    def run_external(command, assertion=None):
        with open("output.txt", 'w') as output_file:
            process = Popen(command.split(), stdout=output_file, stderr=DEVNULL)
            process.wait()
        logger.info("COMMAND")
        logger.info(command)

        if assertion is not None:
            with open("output.txt") as File:
                text = File.read()
                logger.info(text)
        #        assert assertion in text


    pwd = os.getcwd()
    tmpdir_path = mkdtemp()
    logger.info(f"[ ] Current path: {pwd:s}") if verbose else None
    logger.info(f"[ ] Going to temporary path {tmpdir_path:s}") if verbose else None
    os.chdir(tmpdir_path)
    shutil.copyfile(f'{pwd:s}/{pdbfile:s}', 'temp.pdb')

    logger.info("[ ] Interfacing antechamber") if verbose else None
    File = open("tleap.in", "w")
    File.write('''
    source leaprc.gaff\n
    TEMP = loadmol2 temp.mol2\n
    check TEMP \n
    loadamberparams temp.frcmod\n
    saveoff TEMP sus.lib \n
    saveamberparm TEMP temp.prmtop temp.inpcrd\n
    quit\n''')
    File.close()

    logger.info("    - Charge of the molecule is", charge)  if verbose else None
    run_external("antechamber -i temp.pdb -fi pdb -o temp.mol2 -fo mol2 -c bcc -s 2 -nc "+str(charge), assertion="Errors = 0")
    run_external("parmchk2 -i temp.mol2 -f mol2 -o temp.frcmod")
    run_external("tleap -f tleap.in")

    parm = pmd.load_file('temp.prmtop', 'temp.inpcrd')
    parm.save('topol.top', format='gromacs')


    neutralize_charge('topol.top', 'topol2.top', charge=charge)

    shutil.copyfile('topol2.top', f'{pwd:s}/{output:s}')
    logger.info("[ ] Molecule parametrized")  if verbose else None

    os.chdir(pwd)
    shutil.rmtree(tmpdir_path)

import argparse


def neutralize_charge(file_name, output, charge=0):
    File = open(file_name, "r")
    text = File.read()
    File.close()
    moleculetype = ""

    if text.count("[ moleculetype ]") > 1:
        print("ERROR: More than one moleculetype")
    elif ("[ system ]" in text):
        moleculetype = text[text.find(r"[ moleculetype ]"):text.find("[ system ]")]
    else:
        moleculetype = text[text.find("[ moleculetype ]"):]

    top = output
    File = open(top, "w")
    File.write(text[:text.find("[ moleculetype ]")])

    atom = True
    in_atoms = False

    # Correction for charge, should be inside the parmetrization
    sum_of_charge = - np.float(charge)  # we start with the formal charge
    number_of_atoms = 0

    for line in moleculetype.splitlines():
        if in_atoms and len(line) > 0 and line[0] != ";":
            # print(line)
            if len(line.split()) > 7:
                sum_of_charge += np.float(line.split()[6])
                number_of_atoms += 1

        if "[ atoms ]" in line:
            in_atoms = True
        if "[ bonds ]" in line:
            in_atoms = False

    if abs(sum_of_charge) > 0.00001:
        fract = sum_of_charge / number_of_atoms
        fract_rest = sum_of_charge - number_of_atoms * np.round(fract, 6)
        every_nth = int(number_of_atoms / (np.abs(fract_rest) / 0.000001))
        qtot = 0.0
        print("   [ ] Rounding up charges to make molecule neutral, every atom gets additional", -fract)
        print("       ,every atom will be assigned 0.000001 each ", fract_rest)
        atom_nr = 0
        for line in moleculetype.splitlines():
            # print(np.round(fract + 0.000001*np.random.random(),6)) #
            if in_atoms and len(line) > 0 and line[0] != ";" and len(line.split()) > 6:
                line = line[:line.find(';')]
                charge = np.float(line.split()[6]) - np.round(fract + np.sign(fract_rest) * 0.000001 * (
                        atom_nr % every_nth == 0 and every_nth * int(
                    (np.abs(fract_rest) / 0.000001)) > atom_nr), 6)
                qtot += charge  # w

                print("{:>6s}{:>11s}{:>7s}{:>8s}{:>6s}{:>7s}{:>10f}{:>11s} ; qtot {: 6f}".format(*line.split()[:6],
                                                                                                 charge,
                                                                                                 line.split()[7],
                                                                                                 qtot),
                      file=File)  # ,[str(np.round(float(line.split()[6])-fract,6))],line.split()[7]))                else:
                atom_nr += 1
            else:
                print(line, file=File)
                # print(qtot)

            if "[ atoms ]" in line:
                in_atoms = True
            if "[ bonds ]" in line:
                in_atoms = False
    else:
        for line in moleculetype.splitlines():
            print(line, file=File)

    File.close()









def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", help="pdb file")
    parser.add_argument("-charge", default=0, help="Topology of the linker ") # TODO
    parser.add_argument("-o", default='topol.top', help="Output coordination file")
    parser.add_argument("-v", action='store_true', dest='v', help="Be loud")
    parser.set_defaults(v=False)
    return parser.parse_args()


# MAKE it less louder
if __name__ == '__main__':
    args = get_args()
    antechamber(args.f, args.charge, args.o, args.v)