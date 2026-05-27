"""Check ContextCapture license status."""
import ccmasterkernel

print('Version:', ccmasterkernel.version())
print('Edition:', ccmasterkernel.edition())
if ccmasterkernel.isLicenseValid():
    print('License: VALID')
else:
    print('License: INVALID -', ccmasterkernel.lastLicenseErrorMsg())
