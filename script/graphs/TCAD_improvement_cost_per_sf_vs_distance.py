#! /usr/bin/env python

import sys, getopt, math, datetime, os
import locale

from sqlalchemy import create_engine
from sqlalchemy.orm import mapper, sessionmaker
from sqlalchemy.sql.expression import *
import geoalchemy
from geoalchemy import *

from numpy import *
from pylab import *
from matplotlib.ticker import *
from matplotlib.scale import *
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from unum.units import *

from giscrape import orm
from giscrape.orm import *

def main(argv=None):

  fig.suptitle("TCAD Cost/SF Distribution by Distance", fontsize=18, weight='bold')
  shady = WKTSpatialElement("POINT(%s %s)" % (-97.699009500000003, 30.250421899999999) )
  session = Session()

  contexts = session.query(Context).order_by(Context.geom.area)
  boundary = session.query(Context).order_by(-Context.geom.area).first()
  q = session.query(TCAD_2008).filter(TCAD_2008.contexts.any( id = boundary.id )).filter(TCAD_2008.the_geom != None).filter(TCAD_2008.improvemen != None).filter(Listing.size != None)

  trim = int(q.count()/50.0)
  vmax = int( q.order_by(-Listing.price/Listing.size)[trim].price / q.order_by(-Listing.price/Listing.size)[trim].size)
  vmin = int( q.order_by(Listing.price/Listing.size).first().price / q.order_by(Listing.price/Listing.size).first().size )
  step = int( (vmax-vmin)/30.0 )

  X = arange(vmin, vmax, step)

  for i,context in enumerate( contexts.all() ):

    ax = plt.subplot(contexts.count(),1,i+1)

    qi = q.filter(Listing.contexts.any( id = context.id ))

    Y = array( [ qi.filter("listing.price / listing.size >= %s" % x).filter("listing.price / listing.size < %s" % (x + step)).count() for x in X ], dtype=float)

    ax.bar(X,Y, width=step, color='y', edgecolor='y')

    ax.axis([vmin,vmax,0,None])
    ax.set_ylabel(context.name.replace(' ','\n'), rotation=0)

    if not i+1 == contexts.count():
      ax.xaxis.set_major_formatter(NullFormatter())
    else:
      ax.set_xlabel('Asking Price / SF ($/sf)')

    ax.grid(True)

  show()


if __name__ == "__main__":
  sys.exit(main())