"""
Audioop compatibility fix for Python 3.13+
Discord.py requires audioop which was removed in Python 3.13
This provides minimal compatibility stubs
"""
import sys

if sys.version_info >= (3, 13):
    import types
    
    # Create a mock audioop module
    audioop = types.ModuleType('audioop')
    
    # Define stub functions that discord.py uses
    def mul(fragment, width, factor):
        """Multiply fragment by factor"""
        return fragment
    
    def tomono(fragment, width, lfactor, rfactor):
        """Convert stereo to mono"""
        return fragment
    
    def tostereo(fragment, width, lfactor, rfactor):
        """Convert mono to stereo"""
        return fragment
    
    def ratecv(fragment, width, nchannels, inrate, outrate, state, weightA=1, weightB=0):
        """Rate conversion"""
        return fragment, None
    
    def lin2ulaw(fragment, width):
        """Linear to u-law encoding"""
        return fragment
    
    def ulaw2lin(fragment, width):
        """U-law to linear encoding"""
        return fragment
    
    def lin2alaw(fragment, width):
        """Linear to A-law encoding"""
        return fragment
    
    def alaw2lin(fragment, width):
        """A-law to linear encoding"""
        return fragment
    
    def adpcm2lin(fragment, width, state):
        """ADPCM to linear encoding"""
        return fragment, state
    
    def lin2adpcm(fragment, width, state):
        """Linear to ADPCM encoding"""
        return fragment, state
    
    # Assign functions to module
    audioop.mul = mul
    audioop.tomono = tomono
    audioop.tostereo = tostereo
    audioop.ratecv = ratecv
    audioop.lin2ulaw = lin2ulaw
    audioop.ulaw2lin = ulaw2lin
    audioop.lin2alaw = lin2alaw
    audioop.alaw2lin = alaw2lin
    audioop.adpcm2lin = adpcm2lin
    audioop.lin2adpcm = lin2adpcm
    
    # Add constants that discord.py might use
    audioop.ULAW_BIAS = 0x84
    audioop.ULAW_CLIP = 32635
    audioop.ALAW_CLIP = 32635
    
    # Install the mock module
    sys.modules['audioop'] = audioop
    print("🔧 Applied audioop compatibility fix for Python 3.13+")
else:
    print("✅ Python < 3.13 detected - audioop fix not needed") 