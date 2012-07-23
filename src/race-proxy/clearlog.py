"""
clear the log, including some zero xml file
"""

import os
def clearlog(path='.', fpatten='.xml', size=0):
    for file in os.listdir(path):
        if file.endswith(r'.xml'):
            fstat = os.stat(file)
            if fstat.st_size <= size:
                os.remove(file)

def main():
    clearlog()

if __name__ == "__main__":
    main()