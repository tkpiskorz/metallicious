import sys
sys.path.insert(0, '/home/fd05/fd/chem1540/github/cgbind2pmd/')


try:
    from metallicious.main import cgbind2pmd
except:
    from cgbind2pmd.main import cgbind2pmd

f='start.gro'
linker_topol='ligand.top'
metal='Co'
metal_charge=2
fingerprint='Co1'
#fingerprint_style='trunc'

cgbind2gmx = cgbind2pmd()
cgbind2gmx.name_of_binding_side = fingerprint
#cgbind2gmx.fingerprint_style = fingerprint_style

cgbind2gmx.from_coords(f, linker_topol, metal, int(metal_charge))

