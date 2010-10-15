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

  fig = plt.figure()
  
  fig.suptitle("Home Availability by Price", fontsize=18, weight='bold')
  session = Session()
    
  trim = int(session.query(Listing).count()/50.0)
  price_max = int( session.query(Listing).filter(Listing.price != None).order_by(-Listing.price)[trim].price )
  price_min = int( session.query(Listing).filter(Listing.price != None).order_by(Listing.price)[trim].price )
  step = int( (price_max-price_min)/100.0 )

  X = range(price_min, price_max, step)
  Y = [ session.query(Listing).filter(Listing.price >= x).filter(Listing.price < x+step).count() for x in X ]
  C = [ session.query(Listing).filter(Listing.price < x).count() for x in X ]

  ax.bar(X,Y, width=step, color='g', edgecolor='g')
  ax.set_ylabel("Units Available")
  ax.set_xlabel("Asking Price (Million $)")
  ax.grid(True)
  ax.axis([price_min,price_max,None,None])
  ax.xaxis.set_major_formatter(mFormatter)
  
  ax2 = ax.twinx()
  ax2.plot(X,C,'--k')
  ax2.set_ylabel('Cumulative Units')
  ax2.axis([price_min,price_max,None,None])
  ax2.xaxis.set_major_formatter(mFormatter)
  
  if to_show:
    show()

if __name__ == "__main__":
  sys.exit(main())