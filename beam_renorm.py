#! /usr/bin/env python
import aipy as a, numpy as n, pylab as p, optparse, sys
import capo as C
import beamuv

o = optparse.OptionParser()
a.scripting.add_standard_options(o, cal=True)
o.add_option('--cat', dest='cat', default='helm,misc',
    help='A comma-delimited list of catalogs from which sources are to be drawn.  Default is "helm,misc".  Other available catalogs are listed under aip y._src.  Some catalogs may require a separate data file to be downloaded and installed.')
o.add_option('--nside', dest='nside', type='int', default=32,
    help='NSIDE parameter for HEALPix map of beam.')
o.add_option('-o', '--outfile', dest='outfile',
    help='The basename of the output files to create.  If not supplied, just plots source tracks.')
o.add_option('-b','--beam',dest='beam',default=None,
    help='The beam npz file to use.')
             
opts,args = o.parse_args(sys.argv[1:])

afreqs = n.load(args[0])['afreqs']
aa = a.cal.get_aa(opts.cal, afreqs)
srctimes,srcfluxes,x,y,z = C.jcp.read_srcnpz(args, verbose=True)
for src in srcfluxes: srcfluxes[src] = n.mean(srcfluxes[src], axis=1)

srcs = srctimes.keys()
srclist, cutoff, catalogs = a.scripting.parse_srcs(','.join(srcs), opts.cat)
cat = a.cal.get_catalog(opts.cal,srclist)
cat.compute(aa)

_coeffs = beamuv.coeffs_from_file(opts.beam)
beam = beamuv.BeamUV(_coeffs,.150,size=500)

newflux = {}
#x,y,z, = {},{},{}

for k in srcs:
    #for t in srctimes[k]:
    #    aa.set_jultime(t)
    #    cat[k].compute(aa)
    #    xi,yi,zi = cat[k].get_crds('top')
    #    x[k] = x.get(k,[]) + [xi]
    #    y[k] = y.get(k,[]) + [yi]
    #    z[k] = z.get(k,[]) + [zi]
    #x[k],y[k],z[k] = n.array(x[k]), n.array(y[k]), n.array(z[k])
    # XXX Could put possibility of hmap here instead of beam...
    beamtrack = beam.response(x[k], y[k], z[k])**2
    newflux[k] = n.abs(n.sum(beamtrack*srcfluxes[k])/n.sum(beamtrack**2))
    if not opts.outfile:
        import pylab as p
        p.semilogy(srctimes[k], beamtrack * newflux[k])
        p.semilogy(srctimes[k], srcfluxes[k])

fluxes = n.array([newflux[k] for k in srcs])
npzfluxes = n.log10(fluxes)


#print 'Saving source info to', opts.outfile+'.npz'
#n.savez(opts.outfile+'.npz',srcnames=srcs,srcfluxes=npzfluxes)
for src,flx in zip(srcs,npzfluxes):
    print 'flux', src, 10**flx

if not opts.outfile:
    p.show()
    sys.exit(0)

print 'Making beams...'
rebeam = a.map.Map(nside=opts.nside,interp=True)

for j,k in enumerate(srcs):
    srcgains = srcfluxes[k]/fluxes[j]
    for i, meas in enumerate(srcgains):
        pcrd,pwgt = rebeam.crd2px(n.array([x[k][i]]),n.array([y[k][i]]),n.array([z[k][i]]),interpolate=True)
        ncrd,nwgt = rebeam.crd2px(n.array([-x[k][i]]),n.array([-y[k][i]]),n.array([z[k][i]]),interpolate=True)
        pcrd.shape,ncrd.shape = (4,),(4,)
        pwgt.shape,nwgt.shape = (4,),(4,)
        rebeam.add(pcrd,pwgt*(fluxes[j])**2,meas)
        rebeam.add(ncrd,nwgt*(fluxes[j])**2,meas)

print 'Saving source-tracks beam to', opts.outfile+'.fits'
rebeam.to_fits(opts.outfile+'.fits',clobber=True)

