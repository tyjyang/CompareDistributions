import matplotlib
import matplotlib.pyplot as plt
import uproot
import mplhep
import numpy as np
import argparse
import os
import re
import logging
from Utilities import makeSimpleHtml
logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input_files", nargs="*", type=str, help="Input root file(s)", required=True)
parser.add_argument("-s", "--samples", nargs="*", type=str, help="Samples to plot", required=True)
parser.add_argument("-u", "--uncertainties", nargs="*", type=str, help="Uncertainty distributions to plot")
parser.add_argument("-b", "--hist", type=str, help="Distribution to plot", required=True)
parser.add_argument("-c", "--channel", type=str, help="Channel to plot", required=True)
parser.add_argument("-p", "--outputPath", type=str, default="/eos/user/t/tyjyang/www/plots/")
parser.add_argument("-o", "--outputFolder", type=str, default="wmass/pdf_unc/histvar")
parser.add_argument("-a", "--append", type=str, default="", help="string to append to output file name")
parser.add_argument("-r", "--ratioRange", type=float, nargs=2, default=[0.9, 1.1])
parser.add_argument("-x", "--xRange", type=float, nargs=2, default=[])
parser.add_argument("--pdf", type=str)
parser.add_argument("--xlabel", type=str)
parser.add_argument("--scaleleg", type=float, default=1.)

# last two are grouped in the same folder
# the rest are the parent directories for plots scanning multiple parameters
parser.add_argument("--scanorder", type=str, default="pdf,channel,hist,unc")

parser.add_argument("--rawUnc", action='store_true', help="Don't append up or down to uncertainty name")
parser.add_argument("--noHtml", action='store_true', help="Don't make html in output folder")
args = parser.parse_args()
xvar = args.hist
if len(args.samples) > 1 and len(args.input_files) != len(args.samples):
    raise RuntimeError("If more than one input file is specified, each file should be specified per sample")
scanorder = args.scanorder.split(",")

plt.style.use([mplhep.style.ROOT])
# cmap = matplotlib.cm.get_cmap('tab20b')    
cmap = matplotlib.cm.get_cmap('Set1')
# For a small number of clusters, make them pretty
all_colors_ = [matplotlib.colors.rgb2hex(cmap(i)) for i in range(cmap.N)]
all_colors_.insert(0, 'black')

def plotHists(bins, centralName, datasets, ratioRange=[0.9, 1.1], width=1, xlim=[],
        xlabel="", scaleleg=1.):
    fig = plt.figure(figsize=(8*width,8))
    ax1 = fig.add_subplot(4, 1, (1, 3)) 
    ax2 = fig.add_subplot(4, 1, 4) 
    centralHist = datasets[centralName]["hist"]
    for name, dataset in datasets.items():
        hist = dataset["hist"]
        if "down" in name and name.replace("down", "up") in datasets:
            name = ""
        elif "up" in name and name.replace("up", "down") in datasets:
            if "20MeV" in name:
                name = r"m$_{\mathrm{W}} \pm$ 20 MeV" 
            elif "100MeV" in name:
                name = r"m$_{\mathrm{W}} \pm$ 100 MeV" 
            else:
                name = name.replace("up", r"$\pm 1\sigma$")

        args = {"label" : name, "color" : dataset["color"]}
        ax1.hist(bins[:-1], bins=bins, weights=hist, histtype='step', **args)
        ratio = np.divide(hist, centralHist, out=np.zeros_like(hist), where=centralHist!=0)
        ax2.hist(bins[:-1], bins=bins, weights=ratio, histtype='step', **args)
    ax2.set_ylim(ratioRange)
    ax1.set_xticklabels([])
    ax1.legend(fontsize=12)
    ax2.set_xlabel(xlabel)
    ax1.set_ylabel("Events/bin")
    ax2.set_ylabel("$(\\delta N + N)/N$")
    plt.subplots_adjust(left=0.15, right = 0.95)
    if xlim:
        ax1.set_xlim(xlim)
        ax2.set_xlim(xlim)
    ax1.legend(prop={'size' : 20*scaleleg})
    return fig

'''
INPUT -------------------------------------------------------------------------
|* (str) full_xvar: the full name of the hist variable, segmented by "_"
|* (str) str_to_rid: the segment in full_xvar to get rid of, can be in regex
|  
ROUTINE -----------------------------------------------------------------------
|* split the full_xvar in segments separated by "_"
|* get rid of the segments that match str_to_rid
| 
OUTPUT ------------------------------------------------------------------------
|* (str) the shortened string, also in segments of "_"
+------------------------------------------------------------------------------ 
''' 
def shorten_xvar(full_xvar, str_to_rid):
	full_xvar_arr = full_xvar.split("_")
	short_xvar_arr = []
	for element in full_xvar_arr:
		if not re.match(str_to_rid, element): short_xvar_arr.append(element)
	return "_".join(short_xvar_arr)

def compareDistributions():
    samples = args.samples
    filenames = args.input_files 
    uncertainties = [""] + args.uncertainties
    if len(uncertainties) == 2 and len(samples) != 1:
        logging.info("Will plot uncertainty %s for all variations" % uncertainties[0])
        uncertainties = uncertainties*len(args.samples)
    elif len(samples) == 1 and len(uncertainties) > 1:
        logging.info("Assuming sample %s for all plots" % samples[0])
        samples = samples*len(uncertainties)
    if len(filenames) == 1 and len(samples) > 1:
        filenames = filenames*len(samples)
    elif len(filenames) > 1 and len(filenames)+1 == len(uncertainties):
        filenames.insert(0, filenames[0])
    args.unc = "-".join(uncertainties[1:min(4, len(uncertainties))])
    
    outputPath = "/".join([args.outputPath, args.outputFolder] + 
                          [getattr(args, x) for x in scanorder[:-2]])
    if not os.path.isdir(outputPath):
        os.makedirs(outputPath)
    #remove files with a different scanorder 
    os.system("rm " + outputPath + "/" + getattr(args, scanorder[-1]) + "*")
    datasets = {}
    bins = []
    for i, (sample, filename, unc) in enumerate(zip(samples, filenames, uncertainties)):
        print(sample, filename, unc)
        rtfile = uproot.open(filename)    
        cenName = "Central" if unc == "" and len(uncertainties) > 1 else sample

        color = all_colors_[i if not i%2 else len(all_colors_)-i-1]
        if unc == "" or args.rawUnc:
            name = unc
            histname = "%s/%s_%s_%s" % (sample, args.hist, unc, args.channel)
            if unc == "":
                histname = "%s/%s_%s" % (sample, args.hist, args.channel)
                name = "Central" if len(uncertainties) > 1 else sample

            hist,bins = rtfile[histname].to_numpy()
            datasets.update({
                name :
                    { "hist" : hist,
                    "color" : color,
                    },
            })
        else:    
            histUp,bins = rtfile["%s/%s_%sUp_%s" % (sample, args.hist, unc, args.channel)].to_numpy()
            histDown,_ = rtfile["%s/%s_%sDown_%s" % (sample, args.hist, unc, args.channel)].to_numpy()
            if len(uncertainties) > 2 and uncertainties[1] == uncertainties[2]:
                unc = unc+"_"+filename.split('/')[-2].split('_')[-1]
            datasets.update({
                unc + " up": 
                    { "hist" : histUp,
                    "color" : color,
                    },
                unc + " down": 
                    { "hist" : histDown,
                    "color" : color,
                    },
            })
    cenName = "Central" if args.uncertainties else samples[0]
    fig = plotHists(bins, cenName, datasets, ratioRange=args.ratioRange, 
            xlim=args.xRange, xlabel=args.xlabel, scaleleg=args.scaleleg,
            width=(1 if "unrolled" not in args.hist else 2))
    append = uncertainties[1:min(4, len(uncertainties))]
    if args.append:
        append = append + [args.append]
    str_to_rid = "w[mp]munu|minnlo"
    outfile = "%s/%s-%s.pdf" % (
        outputPath, 
        shorten_xvar(getattr(args, scanorder[-2]), str_to_rid), 
        shorten_xvar(getattr(args, scanorder[-1]), str_to_rid))

    fig.savefig(outfile)
    fig.savefig(outfile.replace(".pdf", ".png"))
    logging.info(f"Wrote output file {outfile}")
    if not os.path.exists(outputPath + '/index.php'):
        os.system('cp ~/scripts/index.php ' + outputPath)

    if not args.noHtml:
        makeSimpleHtml.writeHTML(outputPath[:-6], "test")

def main():
    compareDistributions()

if __name__ == "__main__":
    main()
