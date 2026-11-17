"""Independent DVT entry point; shared with GUI worker."""
import sys
from location_studio_mac.dvt import main
if __name__=='__main__':main('dvt_send',sys.argv[1:])
