import matplotlib.pyplot as plt
import uproot
import mplhep
import numpy as np
import argparse
import os
import logging
from Utilities import makeSimpleHtml

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input_files", nargs="*", type=str, help="Input root file(s)", required=True)
parser.add_argument("-s", "--samples", nargs="*", type=str, help="Samples to plot", required=True)
parser.add_argument("-u", "--uncertainties", nargs="*", type=str, help="Uncertainty distributions to plot")
parser.add_argument("-b", "--hist", type=str, help="Distribution to plot", required=True)
parser.add_argument("-c", "--channel", type=str, help="Channel to plot", required=True)
parser.add_argument("-p", "--outputPath", type=str, default=os.path.expanduser("~/www/PlottingResults"))
parser.add_argument("-o", "--outputFolder", type=str, default="Test")
parser.add_argument("-a", "--append", type=str, default="", help="string to append to output file name")
parser.add_argument("-r", "--ratioRange", type=float, nargs=2, default=[0.9, 1.1])
parser.add_argument("--noHtml", action='store_true', help="Don't make html in output folder")
args = parser.parse_args()
xvar = args.hist
if len(args.samples) > 1 and len(args.input_files) != len(args.samples):
    raise RuntimeError("If more than one input file is specified, each file should be specified per sample")

plt.style.use([mplhep.style.ROOT])

def plotHists(bins, centralName, datasets, ratioRange=[0.9, 1.1], width=1):
    fig = plt.figure(figsize=(8*width,8))
    ax1 = fig.add_subplot(4, 1, (1, 3)) 
    ax2 = fig.add_subplot(4, 1, 4) 
    centralHist = datasets[centralName]["hist"]
    for name, dataset in datasets.items():
        hist = dataset["hist"]
        args = {"label" : name, "color" : dataset["color"]}
        ax1.hist(bins[:-1], bins=bins, weights=hist, histtype='step', **args)
        ratio = np.divide(hist, centralHist, out=np.zeros_like(hist), where=centralHist!=0)
        ax2.hist(bins[:-1], bins=bins, weights=ratio, histtype='step', **args)
    ax2.set_ylim(ratioRange)
    ax1.set_xticklabels([])
    ax1.legend()
    print(xvar)
    if xvar == 'ptl':
        xlabel = '$p_{T}^{\\ell}\\,$[GeV]'
    ax2.set_xlabel(xlabel)
    ax1.set_ylabel("Events/bin")
    return fig

def compareDistributions():
    samples = args.samples
    filenames = args.input_files 
    uncertainties = args.uncertainties if args.uncertainties else [""]
    if len(filenames) != len(samples):
        filenames = [filenames]*len(args.samples)
    if len(uncertainties) != len(samples):
        uncertainties = [uncertainties]*len(args.samples)

    outputPath = "/".join([args.outputPath, args.outputFolder, "plots"])
    if not os.path.isdir(outputPath):
        os.makedirs(outputPath)

    datasets = {}
    bins = []
    for sample, filename, unc in zip(samples, filenames, uncertainties):
        print(sample, filename, unc)
        rtfile = uproot.open(filename)    
        hist, bins = rtfile["%s/%s_%s" % (sample, args.hist, args.channel)].to_numpy()
        cenName = "Central" if unc else sample
        datasets.update({cenName : 
                { "hist" : hist,
                "color" : "red"}
        })
        if unc:    
            histUp,_ = rtfile["%s/%s_%sUp_%s" % (sample, args.hist, unc, args.channel)].to_numpy()
            histDown,_ = rtfile["%s/%s_%sDown_%s" % (sample, args.hist, unc, args.channel)].to_numpy()
            datasets.update({
                unc + " up": 
                    { "hist" : histUp,
                    "color" : "blue"
                    },
                unc + " down": 
                    { "hist" : histDown,
                    "color" : "blue"
                    },
            })
    cenName = "Central" if args.uncertainties else samples[0]
    fig = plotHists(bins, cenName, datasets, ratioRange=args.ratioRange)
    append = args.uncertainties 
    if args.append:
        append = append + [args.append]
    outfile = "%s/%s_%s.pdf" % (outputPath, args.hist, "_".join(append))
    fig.savefig(outfile)
    fig.savefig(outfile.replace("pdf", "png"))
    logging.info(f"Wrote output file {outfile}")

    if not args.noHtml:
        makeSimpleHtml.writeHTML(outputPath[:-6], "test")

def main():
    compareDistributions()

if __name__ == "__main__":
    main()
