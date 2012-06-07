#! /usr/bin/env python
"""
Filter in fringe-rate to select (or de-select) fringe rates that correspond to sources fixed
to the celestial sphere.
Author: Aaron Parsons
"""

import aipy as a, numpy as n, sys, os, optparse
import capo as C
import pylab

o = optparse.OptionParser()
a.scripting.add_standard_options(o, cal=True, ant=True, pol=True)
o.add_option('--clean', dest='clean', type='float', default=1e-3,
    help='Deconvolve delay-domain data by the "beam response" that results from flagged data.  Specify a tolerance for termination (usually 1e-2 or 1e-3).')
o.add_option('--minfr', dest='minfr', type='float', default=6e-5,
    help='Minimum fringe rate (in Hz) to allow.  Anything varying slower than this is considered crosstalk.  A negative value indicates nothing should be considered crosstalk.  Default 6e-5')
o.add_option('--rmsky', action='store_true',
    help='Instead of retaining the data corresponding to the sky, remove it.')
o.set_usage('fringe_rate_filter.py [options] *.uv')
o.set_description(__doc__)
opts,args = o.parse_args(sys.argv[1:])

uv = a.miriad.UV(args[0])
inttime = uv['inttime']
aa = a.cal.get_aa(opts.cal, uv['sdf'], uv['sfreq'], uv['nchan'])
del(uv)

def sky_fng_thresh(bl_ew_len, inttime, nints, freq, min_fr=6e-5, neg_fr=-2e-4, max_fr_frac=1.):
    '''For bl_ew_len (the east/west projection) in ns, return the (upper,negative,lower) fringe rate bins 
    that geometrically correspond to the sky.'''
    bin_fr = 1. / (inttime * nints)
    max_bl = bl_ew_len * max_fr_frac
    max_fr = freq * max_bl * 2*n.pi / a.const.sidereal_day
    lthr = min_fr / bin_fr
    nthr = neg_fr / bin_fr
    uthr = max_fr / bin_fr
    uthr, nthr, lthr = n.ceil(uthr).astype(n.int), int(n.floor(nthr)), int(n.floor(lthr))
    return (uthr,nthr,lthr)

def all_sky_fng_thresh(aa, inttime, nints, min_fr=6e-5, neg_fr=-2e-4, max_fr_frac=1.):
    '''Return a dictionary, indexed by baseline, of the (upper,lower) fringe rate
    bins that geometrically correspond to the sky.'''
    filters = {}
    for i in range(len(aa.ants)):
      for j in range(len(aa.ants)):
        if j < i: continue
        bl = aa.ij2bl(i,j)
        bl_len = aa.get_baseline(i,j)
        print i,j, bl_len
        bl_ew_len = n.sqrt(n.dot(bl_len[:2], bl_len[:2]))
        filters[bl] = sky_fng_thresh(bl_ew_len, inttime, nints, aa.get_afreqs(), 
            min_fr=min_fr, neg_fr=neg_fr, max_fr_frac=max_fr_frac)
    return filters

times, dat, flg = C.arp.get_dict_of_uv_data(args, opts.ant, opts.pol, verbose=True)
max_fr = all_sky_fng_thresh(aa, inttime, times.size, min_fr=opts.minfr, max_fr_frac=1.)

for bl in dat:
    # Variables: ufr (upper fringe rate), nfr (negative fringe rate), lfr (lowest fringe rate for xtalk removal)
    ufr,nfr,lfr = max_fr[bl]
    for pol in dat[bl]:
        d = n.where(flg[bl][pol], 0, dat[bl][pol])
        w = n.logical_not(flg[bl][pol]).astype(n.float)
        #window = a.dsp.gen_window(d.shape[0], 'blackman-harris')
        window = 1
        for ch in range(d.shape[1]):
            _d,_w = n.fft.ifft(d[:,ch]*window), n.fft.ifft(w[:,ch]*window)
            gain = n.abs(_w[0])
            print ch, lfr, nfr, ufr[ch], gain
            if gain == 0: continue
            area = n.ones(_d.shape, dtype=n.int)
            area[ufr[ch]+1:nfr] = 0
            _d,info = a.deconv.clean(_d,_w, area=area, tol=opts.clean, stop_if_div=False, maxiter=100)
            _d += info['res'] / gain * area
            if opts.minfr >= 0:
                _d[:lfr+1] = 0
                if lfr > 0: _d[-lfr:] = 0
            if opts.rmsky: d[:,ch] -= n.fft.fft(_d)
            else: d[:,ch] = n.fft.fft(_d)
        dat[bl][pol] = d * w

for filename in args:
    outfile = filename+'X'
    print filename,'->',outfile
    if os.path.exists(outfile):
        print outfile, 'exists.  Skipping...'
        continue
    def mfunc(uv, p, d, f):
        uvw,t,(i,j) = p
        cnt = n.searchsorted(times,t)
        bl = a.miriad.ij2bl(i,j)
        pol = a.miriad.pol2str[uv['pol']]
        try: return p, dat[bl][pol][cnt], flg[bl][pol][cnt]
        except(KeyError): return p, d, f
    uvi = a.miriad.UV(filename)
    uvo = a.miriad.UV(outfile, status='new')
    uvo.init_from_uv(uvi)
    uvo.pipe(uvi, mfunc=mfunc, append2hist='FRINGE RATE FILTER:'+' '.join(sys.argv)+'\n', raw=True)
