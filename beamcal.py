#! /usr/bin/env python
import aipy as a, numpy as n, sys, optparse#, pickle
import capo as C

o = optparse.OptionParser()
o.add_option('--nside', dest='nside', type='int', default=32,
    help='NSIDE parameter for HEALPix map of beam.')
o.add_option('-o', '--outfile', dest='outfile',
    help='The basename of the output files to create.')
o.add_option('--fluxcal',dest='fluxcal',default='cyg,10622.92',
    help='The source to use as a flux calibrator.')
opts,args = o.parse_args(sys.argv[1:])

afreqs = n.load(args[0])['afreqs']
srctimes,srcfluxes,x,y,z = C.jcp.read_srcnpz(args, verbose=True)
for src in srcfluxes: srcfluxes[src] = n.mean(srcfluxes[src], axis=1)
srcs = srctimes.keys()

beama = a.map.Map(opts.nside,interp=True)
beamb = a.map.Map(opts.nside,interp=True)

calsrc,calflux = opts.fluxcal.split(',')
calflux = float(calflux)

print 'Calculating source tracks...'
track = {}
tracks = n.array([]) 
for k in srcs:
    #valid = n.where(z[k] > 0, 1, 0)
    #x[k], y[k], z[k] = n.compress(valid, x[k]), n.compress(valid,y[k]), n.compress(valid, z[k])
    track[k] = n.append(n.unique(beama.crd2px(x[k],y[k],z[k],interpolate=True)[0]), n.unique(beama.crd2px(-x[k],-y[k],z[k],interpolate=True)[0]))
    #track[k] = n.unique(n.append(beama.crd2px(x[k],y[k],z[k]), beam.crd2px(-x[k],-y[k],z[k])))
    tracks = n.append(tracks,track[k])
tracks = tracks.astype(n.long)

print 'Determining crossing points...'
cnt = {}
for i in xrange(max(tracks)+1):
    cnt[i] = n.where(tracks == i)[0].shape[0]
    crossing_pixels = n.where(n.array(cnt.values()) > 1)[0]

print 'Averaging measurements within a pixel...'
fluxtrack,wgttrack,sqwgttrack = {},{},{}
S,C,w,wM = [],[],[],[]
for k in srcs:
    fluxtrack[k],wgttrack[k],sqwgttrack[k] = {},{},{}
    for i, meas in enumerate(srcfluxes[k]):
        pcrd,pwgt = beama.crd2px(n.array([x[k][i]]),n.array([y[k][i]]),n.array([z[k][i]]),interpolate=True)
        ncrd,nwgt = beama.crd2px(n.array([-x[k][i]]),n.array([-y[k][i]]),n.array([z[k][i]]),interpolate=True)
        for ind,crd in enumerate(pcrd[0]):
            if crd in crossing_pixels:
                if not fluxtrack[k].has_key(crd):
                    fluxtrack[k][crd] = pwgt[0][ind]*meas
                    wgttrack[k][crd] = pwgt[0][ind]
                    sqwgttrack[k][crd] = (pwgt[0][ind])**2
                else:
                    fluxtrack[k][crd] += pwgt[0][ind]*meas
                    wgttrack[k][crd] += pwgt[0][ind]
                    sqwgttrack[k][crd] += (pwgt[0][ind])**2
        for ind,crd in enumerate(ncrd[0]):
            if crd in crossing_pixels:
                if not fluxtrack[k].has_key(crd):
                    fluxtrack[k][crd] = nwgt[0][ind]*meas
                    wgttrack[k][crd] = nwgt[0][ind]
                    sqwgttrack[k][crd] = (nwgt[0][ind])**2
                else:
                    fluxtrack[k][crd] += nwgt[0][ind]*meas
                    wgttrack[k][crd] += nwgt[0][ind]
                    sqwgttrack[k][crd] += (nwgt[0][ind])**2
    for crd in fluxtrack[k].keys():
        S.append(k)
        C.append(crd)
        fluxtrack[k][crd] /= wgttrack[k][crd]
        weight = (fluxtrack[k][crd]**2)*(wgttrack[k][crd])
        w.append(weight)
        wM.append(n.log10(fluxtrack[k][crd])*(fluxtrack[k][crd]**2)*(wgttrack[k][crd]))
        wgttrack[k][crd] = weight

#print n.where(n.array(w)==0)
print 'Constructing matrices...'
dC,dS = {},{}
for i,c in enumerate(crossing_pixels):
    dC[c] = i
for i,k in enumerate(srcs):
    if not dS.has_key(k): dS[k] = i
neq = len(wM)
npix = len(crossing_pixels)
nsrcs = len(srcs)
A = n.zeros((neq+1,npix+nsrcs),dtype=n.float32)

for k in srcs:
    for ind,wgt in enumerate(w):
        A[ind,dC[C[ind]]] = wgt
        A[ind,npix+dS[S[ind]]] = wgt
    if k == calsrc:
        A[-1,npix+dS[calsrc]] = 1e16

wM.append(1e16*n.log10(calflux))
wM = n.array(wM,dtype=n.float32)

print 'Solving equation...'
#B = n.dot(n.linalg.inv(n.dot(n.transpose(A),A)),n.dot(n.transpose(A),wM))
B = n.linalg.lstsq(A,wM)
for src,flx in zip(srcs,B[0][-nsrcs:]):
    print 'flux', src, 10**flx

print 'Making beams...'
#bm = 10**(B[:-nsrcs])
bm = 10**(B[0][:-nsrcs])
beama.add(crossing_pixels,n.ones_like(bm),bm)
outnamea = opts.outfile + 'a.fits'
print 'Saving crossing-points beam to', outnamea
beama.to_fits(outnamea, clobber=True)

outnameb = opts.outfile + 'b.fits'
fluxes = 10**(B[0][npix:])
for j,k in enumerate(srcs):
    srcgains = srcfluxes[k]/fluxes[j]
    for i, meas in enumerate(srcgains):
        pcrd,pwgt = beama.crd2px(n.array([x[k][i]]),n.array([y[k][i]]),n.array([z[k][i]]),interpolate=True)
        ncrd,nwgt = beama.crd2px(n.array([-x[k][i]]),n.array([-y[k][i]]),n.array([z[k][i]]),interpolate=True)
        pcrd.shape,ncrd.shape = (4,),(4,)
        pwgt.shape,nwgt.shape = (4,),(4,)
        beamb.add(pcrd,pwgt*(fluxes[j])**2,meas)
        beamb.add(ncrd,nwgt*(fluxes[j])**2,meas)
print 'Saving source-tracks beam to', outnameb
beamb.to_fits(outnameb,clobber=True)
