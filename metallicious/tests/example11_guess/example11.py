from metallicious.load_fingerprint import guess_fingerprint
metal='Pd'

fp1 = guess_fingerprint('cage.xyz', 0, metal_name = metal, fingerprint_guess_list=['Pd2d', 'PdB1', 'PdB2'])
fp2 = guess_fingerprint('cage2.xyz', 184, metal_name = metal, fingerprint_guess_list=['Pd2d', 'PdB1', 'PdB2'])
fp3 = guess_fingerprint('cage3.xyz', 160, metal_name = metal, fingerprint_guess_list=['Pd2d', 'PdB1', 'PdB2'])

if fp1 == 'Pd2d':
    print("[+] FP1 correct!")
else:
    print("[-] FP1 incorrect!")

if fp2 == 'PdB1':
    print("[+] FP2 correct!")
else:
    print("[-] FP2 incorrect!")

if fp3 == 'Pd2d':
    print("[+] FP3 correct!")
else:
    print("[-] FP3 incorrect!")

