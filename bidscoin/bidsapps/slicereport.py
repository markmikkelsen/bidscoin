#!/usr/bin/env python3
"""
A wrapper around the 'slicesdir' reporting tool (https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/Miscvis)
that generates a web page with a row of image slices for each subject in the BIDS repository.
In this way you can do a simple visual quality control of any datatype in your BIDS repository

Requires an existing installation of FSL/slicesdir
"""

import argparse
import logging
import subprocess
from pathlib import Path
try:
    from bidscoin import bidscoin
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).parents[1]))             # This should work if bidscoin was not pip-installed
    import bidscoin


def slicereport(bidsdir: str, pattern: str, outlinepattern: str, overlayimage: str, edgethreshold: str, secondslice: bool):
    """
    :param bidsdir:         The bids-directory with the subject data
    :param pattern:         Globlike search pattern to select the images in bidsdir to be reported, e.g. 'anat/*_T1w*'
    :param outlinepattern:  Globlike search pattern to select a common red-outline image on top of all images
    :param overlayimage:    A common red-outline image that is projected on top of all images
    :param edgethreshold:   The specified threshold for edges (if >0 use this proportion of max-min, if <0, use the absolute value)
    :param secondslice:     Output every second axial slice rather than just 9 ortho slices
    :return:
    """

    # Input checking
    bidsdir = Path(bidsdir).resolve()
    report  = bidsdir/'derivatives'/'slicesdir'
    if not bidsdir.is_dir():
        print(f"Could not find the bids folder: {bidsdir}")
        return
    if overlayimage and not Path(overlayimage).is_file():
        print(f"Could not find the common overlay image: {overlayimage}")
        return

    # Start logging (no logfile)
    bidscoin.setup_logging()

    # Get the list of subjects/sessions
    subjects = bidscoin.lsdirs(bidsdir, 'sub-*')
    filelist = []
    for subject in subjects:
        sessions = bidscoin.lsdirs(subject, 'ses-*')
        if not sessions:
            sessions = [subject]
        for session in sessions:

            # Search for images to report
            LOGGER.info(f"Searching in: {session}")
            images = sorted([str(match) for match in session.glob(pattern) if '.nii' in match.suffixes])
            if outlinepattern:
                outline = sorted([str(match) for match in session.glob(outlinepattern) if '.nii' in match.suffixes]) if outlinepattern else None
                if len(outline) != len(images):
                    LOGGER.error(f"Nr of outline images ({len(outline)}) in {session} should be the same as the number of underlying images ({len(images)})")
                    return
                images = [item for pair in zip(images,outline) for item in pair]

            filelist += images

    if not filelist:
        LOGGER.info(f"Could not find images using: {pattern}")
        return

    # Generate the report using: slicesdir [-o] [-p <image>] [-e <thr>] [-S] <filelist>
    command = f"slicesdir {'-o'                if outlinepattern else ''}"\
                       f" {'-p '+overlayimage  if overlayimage   else ''}"\
                       f" {'-e '+edgethreshold if edgethreshold  else ''}"\
                       f" {'-S'                if secondslice    else ''}"\
                       f" {' '.join(filelist)}"
    LOGGER.info(f"Running:\n{command}")
    report.parent.mkdir(exist_ok=True)
    process = subprocess.run(command, cwd=report.parent, shell=True, capture_output=True, text=True)
    if process.stderr or process.returncode != 0:
        LOGGER.error(f"Errorcode {process.returncode}:\n{process.stdout}\n{process.stderr}")
        return
    elif process.stdout:
        LOGGER.success(f"\n{process.stdout}")


def main():
    """Console script usage"""

    class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter): pass

    parser = argparse.ArgumentParser(formatter_class=CustomFormatter,
                                     description=__doc__,
                                     epilog='examples:\n'
                                            '  slicereport myproject/bids anat/*_T1w*\n'
                                            '  slicereport myproject/bids/derivatives/deface anat/*_T1w*\n'
                                            '  slicereport myproject/bids extra_data/*_T1w* -o anat/*_T1w* -e 0.05       # extra_data = defaced\n'
                                            '  slicereport myproject/bids fmap/*_phasediff* -o fmap/*_magnitude1*\n'
                                            '  slicereport myproject/bids/derivatives/fmriprep anat/*run-?_desc-preproc_T1w* -o anat/*run-?_label-GM*\n ')
    parser.add_argument('bidsfolder',               help='The bids-directory with the subject data')
    parser.add_argument('pattern',                  help="Globlike search pattern to select the images to be reported, e.g. 'anat/*_T2starw*'")
    parser.add_argument('-o','--outlinepattern',    help="Globlike search pattern to select red outline images that are projected on top of the corresponding images (i.e. 'outlinepattern' must yield the same number of images as 'pattern'")
    parser.add_argument('-p','--overlayimage',      help='A common red-outline image that is projected on top of all images')
    parser.add_argument('-e','--edgethreshold',     help='The specified threshold for edges (if >0 use this proportion of max-min, if <0, use the absolute value)')
    parser.add_argument('-s','--secondslice',       help='Output every second axial slice rather than just 9 ortho slices', action='store_true')
    args = parser.parse_args()

    slicereport(bidsdir        = args.bidsfolder,
                pattern        = args.pattern,
                outlinepattern = args.outlinepattern,
                overlayimage   = args.overlayimage,
                edgethreshold  = args.edgethreshold,
                secondslice    = args.secondslice)


if __name__ == '__main__':
    LOGGER = logging.getLogger(f"bidscoin.{Path(__file__).stem}")
    main()

else:
    LOGGER = logging.getLogger(__name__)
