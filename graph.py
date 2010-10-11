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

_Functions = [
  'run',
  'appraisal_accuracy',
  'cost_per_sf_vs_size',
  'age_vs_distance_scatter',
  'size_vs_distance_scatter',
  'size_vs_distance',
  'cost_per_sf_vs_distance',
  'cost_per_sf_vs_distance_scatter',
  'cost_vs_distance_scatter',
  'cost_vs_distance',
  'size_vs_age',
  'new_sale_size_distribution',
  'new_cost_per_sf_distribution',
  'new_sale_price_distribution',
  'recent_median_cost_vs_age',
  'median_cost_vs_age',
  'sale_size_distribution',
  'rent_per_sf_distribution',
  'cost_per_sf_distribution',
  'sale_price_distribution',
  'rental_price_distribution']
	
engine = create_engine('postgresql://postgres:kundera2747@localhost/gisdb', echo=True)
metadata = orm.Base.metadata
metadata.create_all(engine) 
Session = sessionmaker(bind=engine)
  
locale.setlocale(locale.LC_ALL)
mFormatter = ticker.FuncFormatter(lambda x,pos: str(x/1000000.0)+'M' )
yFormatter = ticker.FuncFormatter(lambda x,pos: "'"+str(x)[-2:] )
fig = plt.figure()

def run():
  sale_price_distribution(fig.add_subplot(1,2,1), False)
  rental_price_distribution(fig.add_subplot(1,2,2), False)
  
  show()
  
#histogram array by distance - price/rent/floor area/age
#income distribution vs rent/cost distribution
#time to sell vs asking price
#time to sell vs size
#time to sell vs bed & baths
#median rent ratio by floor area (control for bed/bath? include bars?)
#floor area vs age


# TCAD '08 doesn't include the size of the structure
def TCAD_improvement_cost_per_sf_vs_distance():
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
  
def appraisal_accuracy():
  fig.suptitle("Ratio Distribution of Asking Price to TCAD Appraisal", fontsize=18, weight='bold')
  session = Session()
  
  q = session.query(Listing).join(TCAD_2008).filter(TCAD_2008.marketvalu > 1000).filter(Listing.price > 1000)
  
  X = [ x.price / ( x.tcad_2008_parcel.marketvalu )  for x in q.all() ]
  Y = [ x.price for x in q.all() ]
  
  ax = plt.subplot(111)
  ax.hist(X,200,(0,2.5), color='g', edgecolor='g')
  ax.grid(True)
  for line in ax.get_ygridlines():
    line.set_alpha(0)

  ax2 = ax.twinx() 
  ax2.hist(X,1000,(0,10), normed=True, histtype='step', cumulative=True, color='k')
  ax2.grid(True)
  ax2.axis([0,2.5,0,1])
  #ax.set_xticks(np.arange(0,5,.5))
  ax2.set_yticks(np.arange(0,1,.1))
  #ax2.yaxis.set_major_formatter(mFormatter)
  #ax2.xaxis.set_major_formatter(yFormatter)
  
  show()
  
def cost_per_sf_vs_size():
  fig.suptitle("Cost/SF vs Size", fontsize=18, weight='bold')
  shady = WKTSpatialElement("POINT(%s %s)" % (-97.699009500000003, 30.250421899999999) )
  session = Session()
  q = session.query(Listing).filter(Listing.geom != None).filter(Listing.price != None).filter(Listing.size != None)
  
  context = q.filter(Listing.geom.transform(32139).distance(shady.transform(32139)) < (2.5 * mile).asNumber(m) ).order_by(-Listing.geom.transform(32139).distance(shady.transform(32139)))

  X = [ x.price / x.size for x in context.all() ]
  Y = [ x.size for x in context ]
  S = 20*array( [ (session.scalar(x.geom.transform(32139).distance(shady.transform(32139))) * m ).asNumber(mile) for x in context ], dtype=float )**3
  
  ax = plt.subplot(111)
  
  ax.scatter(X,Y,S,'c', alpha=.75)
  
  ax.set_title('Dot size denotes distance from site')
  ax.set_xlabel('Asking Price / SF ($/sf)')
  ax.set_ylabel('Size (sf)')
    
  ax.grid(True)
  ax.axis([0,400,500,2000])

  show()
  
def age_vs_distance_scatter():
  fig.suptitle("Age vs Distance", fontsize=18, weight='bold')
  shady = WKTSpatialElement("POINT(%s %s)" % (-97.699009500000003, 30.250421899999999) )
  session = Session()
  q = session.query(Listing).filter(Listing.geom != None).filter(Listing.year_built != None).filter(Listing.geom.transform(32139).distance(shady.transform(32139)) < (2.5 * mile).asNumber(m) ).order_by(-Listing.year_built)
  
  X = [ (session.scalar(x.geom.transform(32139).distance(shady.transform(32139))) * m ).asNumber(mile) for x in q[:-5] ]
  Y = [ x.year_built for x in q[:-5] ]
  
  ax = plt.subplot(111)
  ax.plot(X,Y,'om')
  ax.grid(True)
  ax.set_ylabel("Year Built")
  ax.set_xlabel("Distance from Site (miles)")
  
  show()
  
def size_vs_distance_scatter():
  fig.suptitle("Size vs Distance", fontsize=18, weight='bold')
  shady = WKTSpatialElement("POINT(%s %s)" % (-97.699009500000003, 30.250421899999999) )
  session = Session()
  q = session.query(Listing).filter(Listing.geom != None).filter(Listing.size != None).filter(Listing.geom.transform(32139).distance(shady.transform(32139)) < (2.5 * mile).asNumber(m) ).order_by(Listing.size)
  
  X = [ (session.scalar(x.geom.transform(32139).distance(shady.transform(32139))) * m ).asNumber(mile) for x in q[:-5] ]
  Y = [ x.size for x in q[:-5] ]
  
  ax = plt.subplot(111)
  ax.plot(X,Y,'oc')
  ax.grid(True)
  ax.set_ylabel("Size (sf)")
  ax.set_xlabel("Distance from Site (miles)")
  
  show()
  
def size_vs_distance():
  fig.suptitle("Size Distribution by Distance", fontsize=18, weight='bold')
  shady = WKTSpatialElement("POINT(%s %s)" % (-97.699009500000003, 30.250421899999999) )
  session = Session()

  contexts = session.query(Context).order_by(Context.geom.area)
  boundary = session.query(Context).order_by(-Context.geom.area).first()
  q = session.query(Listing).filter(Listing.contexts.any( id = boundary.id )).filter(Listing.geom != None).filter(Listing.size != None)
  
  trim = int(q.count()/10.0)
  vmax = int( q.order_by(-Listing.size)[trim].size )
  vmin = int( q.order_by(Listing.size).first().size )
  step = int( (vmax-vmin)/30.0 )
  
  X = range(vmin, vmax, step)
  
  for i,context in enumerate( contexts.all() ):
    
    ax = plt.subplot(contexts.count(),1,i+1)
    
    qi = q.filter(Listing.contexts.any( id = context.id ))
    
    Y = array( [ qi.filter(Listing.size >= x).filter(Listing.size < x+step).count() for x in X ], dtype=float )
    
    ax.bar(X,Y, width=step, color='c', edgecolor='c')

    ax.axis([vmin,vmax,0,None])
    #ax.set_xticks(np.arange(0,vmax,250000))
    ax.set_ylabel(context.name.replace(' ','\n'), rotation=0)
    
    if not i+1 == contexts.count():
      ax.xaxis.set_major_formatter(NullFormatter())
    else:
      #ax.xaxis.set_major_formatter(mFormatter)
      ax.set_xlabel('Size (sf)')
    
    ax.grid(True)
    
  show()

def cost_per_sf_vs_distance_scatter():
  fig.suptitle("Cost/sf vs Distance", fontsize=18, weight='bold')
  shady = WKTSpatialElement("POINT(%s %s)" % (-97.699009500000003, 30.250421899999999) )
  session = Session()
  q = session.query(Listing).filter(Listing.geom != None).filter(Listing.size != None).filter(Listing.price != None).filter(Listing.geom.transform(32139).distance(shady.transform(32139)) < (2.5 * mile).asNumber(m) ).order_by(Listing.price/Listing.size)
  
  X = [ (session.scalar(x.geom.transform(32139).distance(shady.transform(32139))) * m ).asNumber(mile) for x in q[:-5] ]
  Y = [ x.price / x.size for x in q[:-5] ]
  
  ax = plt.subplot(111)
  ax.plot(X,Y,'oy')
  ax.grid(True)
  ax.set_ylabel("Asking Price / SF ($/sf)")
  ax.set_xlabel("Distance from Site (miles)")
  
  show()
  
def cost_per_sf_vs_distance():
  fig.suptitle("Cost/SF Distribution by Distance", fontsize=18, weight='bold')
  shady = WKTSpatialElement("POINT(%s %s)" % (-97.699009500000003, 30.250421899999999) )
  session = Session()
  
  contexts = session.query(Context).order_by(Context.geom.area)
  boundary = session.query(Context).order_by(-Context.geom.area).first()
  q = session.query(Listing).filter(Listing.contexts.any( id = boundary.id )).filter(Listing.geom != None).filter(Listing.price != None).filter(Listing.size != None)
  
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
  
def cost_vs_distance_scatter():
  fig.suptitle("Cost vs Distance", fontsize=18, weight='bold')
  shady = WKTSpatialElement("POINT(%s %s)" % (-97.699009500000003, 30.250421899999999) )
  session = Session()
  q = session.query(Listing).filter(Listing.geom != None).filter(Listing.price != None).filter(Listing.geom.transform(32139).distance(shady.transform(32139)) < (2.5 * mile).asNumber(m) ).order_by(Listing.price)
  
  X = [ (session.scalar(x.geom.transform(32139).distance(shady.transform(32139))) * m ).asNumber(mile) for x in q[:-5] ]
  Y = [ x.price for x in q[:-5] ]
  
  ax = plt.subplot(111)
  ax.plot(X,Y,'og')
  ax.grid(True)
  ax.yaxis.set_major_formatter(mFormatter)
  ax.set_ylabel("Asking Price ($)")
  ax.set_xlabel("Distance from Site (miles)")
  
  show()
  
def cost_vs_distance():
  fig.suptitle("Cost Distribution by Distance", fontsize=18, weight='bold')
  shady = WKTSpatialElement("POINT(%s %s)" % (-97.699009500000003, 30.250421899999999) )
  session = Session()
  
  contexts = session.query(Context).order_by(Context.geom.area)
  boundary = session.query(Context).order_by(-Context.geom.area).first()
  q = session.query(Listing).filter(Listing.contexts.any( id = boundary.id )).filter(Listing.geom != None).filter(Listing.price != None)
  
  trim = int(q.count()/50.0)
  price_max = int( q.order_by(-Listing.price)[trim].price )
  price_min = int( q.order_by(Listing.price).first().price )
  step = int( (price_max-price_min)/30.0 )
  
  X = range(price_min, price_max, step)
  
  for i,context in enumerate( contexts.all() ):
    
    ax = plt.subplot(contexts.count(),1,i+1)
    
    qi = q.filter(Listing.contexts.any( id = context.id ))
    
    Y = array( [ qi.filter(Listing.price >= x).filter(Listing.price < x+step).count() for x in X ], dtype=float )
    
    ax.bar(X,Y, width=step, color='g', edgecolor='g')

    ax.axis([price_min,price_max,0,None])
    ax.set_xticks(np.arange(0,price_max,50000))
    ax.set_ylabel(context.name.replace(' ','\n'), rotation=0)
    
    if not i+1 == contexts.count():
      ax.xaxis.set_major_formatter(NullFormatter())
    else:
      ax.xaxis.set_major_formatter(mFormatter)
      ax.set_xlabel('Asking Price ($)')
    
    ax.grid(True)
    
  show()

def size_vs_age( ax = fig.add_subplot(1,1,1), to_show=True):
  fig.suptitle("Size Distribution by Age", fontsize=18, weight='bold')
  
  session = Session()
  
  q = session.query(Listing).filter(Listing.year_built != None).filter(Listing.size != None)
  total = q.count()
  trim = int( total * .01 )
  first_date = q.order_by(asc(Listing.year_built))[trim].year_built
  last_date = q.order_by(desc(Listing.year_built)).first().year_built
  step = int((last_date - first_date)/12. )
  
  def sizes(start,end):
    return [ x.size for x in q.filter('listing.year_built >= %s' % start).filter('listing.year_built < %s' % end).all() ]
    
  X = arange(first_date, last_date, step)
  Y = [ sizes(x,x+step) for x in X ]
  C = [ len(y) for y in Y ]
  

  ax.set_title("Boxes show median and quartiles, lines show inner quartile range")   
  ax.set_xlabel("Year Built")
  p1=ax.plot(X,C,'--k', alpha=.5, zorder=-1)
  ax.set_ylabel('Sample Size')
  
  ax2 = ax.twinx() 
  ax2.boxplot(Y, sym='', whis=1.5, positions=X, widths=(.5*step))
  ax2.set_ylabel("Size Distribution (sf)")
  ax2.grid(True)
  ax2.axis([first_date-(step/2),last_date,None,None])
  #ax2.yaxis.set_major_formatter(mFormatter)
  ax2.xaxis.set_major_formatter(yFormatter)
  
  legend([p1],['Sample Size'], loc=2)
  show()  

def new_sale_size_distribution( ax = fig.add_subplot(1,1,1), to_show = True):
  fig.suptitle("New Home Size Distribution", fontsize=18, weight='bold')
  
  session = Session()
  
  area_query = session.query(Listing).filter(Listing.size != None)
  total = area_query.count()
  trim = int( total * .02 )
  max_area = area_query.order_by(desc(Listing.size))[trim].size
  min_area = area_query.order_by(asc(Listing.size)).first().size
  step = int( (max_area - min_area)/100.0 )
  
  X = arange(min_area, max_area, step)
  Y = array( [ area_query.filter("listing.size >= %s" % str(x)).filter("listing.size < %s" % str(x+step)).count() for x in X ], dtype=float )
  C = array( [ area_query.filter("listing.size < %s" % x).count() for x in X], dtype = float )
  nY = array( [ area_query.filter("listing.size >= %s" % str(x)).filter("listing.size < %s" % str(x+step)).filter(Listing.year_built >= 2009).count() for x in X ], dtype=float )
  nC = array( [ area_query.filter("listing.size < %s" % x).filter(Listing.year_built >= 2009).count() for x in X], dtype = float )
  
  ax.bar(X,100*nY/area_query.filter(Listing.year_built >= 2009).count(), width=step, color='c',edgecolor='c')
  ax.bar(X,100*Y/area_query.count(), width=step, color='k', linewidth=0, alpha=.3)
  ax.set_ylabel("Units Available (%)")
  ax.set_xlabel("Size (sf)")
  ax.axis([min_area,max_area,0,None])
  ax.grid(True)
  for line in ax.get_ygridlines():
    line.set_alpha(0)
      
  ax2 = ax.twinx()
  ax2.plot(X,100*C/area_query.count(),'k', alpha=.3, lw=2)
  ax2.plot(X,100*nC/area_query.filter(Listing.year_built >= 2009).count(),'k', lw=2)
  ax2.set_ylabel('Cumulative Units (%)')
  ax2.axis([min_area,max_area,0,100])
  ax2.set_yticks(np.arange(0,101,10))
  ax.set_xticks(np.arange(0,max_area,500))
  ax2.grid(True)
  
  ax.set_title("(All shown in grey)")
  show()
  
def new_cost_per_sf_distribution( ax = fig.add_subplot(1,1,1), to_show = True ):
  fig.suptitle("New Home Price/sf Distribution", fontsize=18, weight='bold')
  session = Session()

  per_sf_query = session.query(Listing).filter(Listing.price != None).filter(Listing.size != None).order_by(asc(Listing.price / Listing.size))
  trim = int( per_sf_query.count() * .01 )
  per_sf_min = int( per_sf_query.first().price / per_sf_query.first().size )
  per_sf_query = session.query(Listing).filter(Listing.price != None).filter(Listing.size != None).order_by(desc(Listing.price / Listing.size))
  per_sf_max = int( per_sf_query[trim].price / per_sf_query[trim].size )

  step = int( (per_sf_max-per_sf_min)/100.0 )

  X = arange(per_sf_min, per_sf_max, step)
  Y = array( [ per_sf_query.filter("listing.price / listing.size >= %s" % x).filter("listing.price / listing.size < %s" % (x + step)).count() for x in X ], dtype=float)
  nY = array( [ per_sf_query.filter("listing.price / listing.size >= %s" % x).filter("listing.price / listing.size < %s" % (x + step)).filter(Listing.year_built >= 2009).count() for x in X ], dtype=float)
  C = array( [ per_sf_query.filter("listing.price / listing.size < %s" % (x + step)).count() for x in X ], dtype=float)
  nC = array( [ per_sf_query.filter("listing.price / listing.size < %s" % (x + step)).filter(Listing.year_built >= 2009).count() for x in X ], dtype=float)
  
  ax.bar(X,100 * nY / per_sf_query.filter(Listing.year_built >= 2009).count(), width=step, color='y', edgecolor='y')
  ax.bar(X,100 * Y / per_sf_query.count(), width=step, color='k', linewidth=0, alpha=.3)
  ax.set_ylabel("Units Available (%)")
  ax.set_xlabel("Asking Price / sf ($/sf)")
  ax.axis([per_sf_min,per_sf_max,0,None])
  ax.grid(True)
  for line in ax.get_ygridlines():
    line.set_alpha(0)
     
  ax2 = ax.twinx()
  ax2.plot(X,100*C/per_sf_query.count(),'k', alpha=.3, lw=2)
  ax2.plot(X,100*nC/per_sf_query.filter(Listing.year_built >= 2009).count(),'k', lw=2)
  ax2.set_ylabel('Cumulative Units (%)')
  ax2.axis([per_sf_min,per_sf_max,0,100])
  ax2.set_yticks(np.arange(0,101,10))
  ax.set_xticks(np.arange(0,per_sf_max,50))
  ax2.grid(True)
    
  ax.set_title("(All shown in grey)")
  show()
  
def new_sale_price_distribution( ax = fig.add_subplot(1,1,1), to_show = True ):
  fig.suptitle("New Home Availability by Price", fontsize=18, weight='bold')
  session = Session()
    
  trim = int(session.query(Listing).count()/50.0)
  price_max = int( session.query(Listing).filter(Listing.price != None).order_by(-Listing.price)[trim].price )
  price_min = int( session.query(Listing).filter(Listing.price != None).order_by(Listing.price)[trim].price )
  step = int( (price_max-price_min)/100.0 )

  X = range(price_min, price_max, step)
  Y = array( [ session.query(Listing).filter(Listing.price >= x).filter(Listing.price < x+step).count() for x in X ], dtype=float )
  nY = array( [session.query(Listing).filter(Listing.price >= x).filter(Listing.price < x+step).filter(Listing.year_built >= 2009).count() for x in X ], dtype=float )
  C = array( [ session.query(Listing).filter(Listing.price < x).count() for x in X ], dtype=float )
  nC = array([ session.query(Listing).filter(Listing.price < x).filter(Listing.year_built >= 2009).count() for x in X ], dtype=float )
  
  ax.bar(X,100*nY / session.query(Listing).filter(Listing.year_built >= 2009).count(), width=step, color='g', edgecolor='g')
  ax.bar(X,100*Y / session.query(Listing).count(), width=step, color='k', linewidth=0, alpha=.3)
  ax.set_ylabel("Units Available (%)")
  ax.set_xlabel("Asking Price (Million $)")
  ax.axis([price_min,price_max,None,None])
  ax.xaxis.set_major_formatter(mFormatter)
  ax.axis([price_min,price_max,0,None])
  ax.grid(True)
  for line in ax.get_ygridlines():
    line.set_alpha(0)
  
  ax2 = ax.twinx()
  ax2.plot(X,100*C / session.query(Listing).count(),'k', alpha = .3, lw=2)
  ax2.plot(X,100*nC / session.query(Listing).filter(Listing.year_built >= 2009).count(),'k', lw=2)
  ax2.set_ylabel('Cumulative Units (%)')
  ax2.axis([price_min,price_max,0,100])
  ax2.xaxis.set_major_formatter(mFormatter)
  ax2.set_yticks(np.arange(0,101,10))
  ax.set_xticks(np.arange(0,price_max,250000))
  ax2.grid(True)
  
  ax.set_title("(All shown in grey)")
  if to_show:
    show()
    
def recent_median_cost_vs_age( ax = fig.add_subplot(1,1,1), to_show=True):
  fig.suptitle("Asking Price Distribution by Age, 1996-2010", fontsize=18, weight='bold')
  
  session = Session()
  
  q = session.query(Listing).filter(Listing.year_built != None).filter(Listing.price != None).filter(Listing.year_built >= 1995)
  total = q.count()

  
  def prices(year):
    return [ x.price for x in q.filter('listing.year_built = %s' % year).all() ]
    
  X = arange(1996, 2011, 1)
  Y = [ prices(x) for x in X ]
  C = [ len(y) for y in Y ]
  

  ax.set_title("Boxes show median and quartiles, lines show inner quartile range")   
  ax.set_xlabel("Year Built")
  p1=ax.plot(X,C,'--k', alpha=.5, zorder=-1)
  ax.set_ylabel('Sample Size')
  
  ax2 = ax.twinx() 
  ax2.boxplot(Y, sym='', whis=1.5, positions=X, widths=.5)
  ax2.set_ylabel("Asking Price Distribution ($)")
  ax2.grid(True)
  ax2.yaxis.set_major_formatter(mFormatter)
  ax2.xaxis.set_major_formatter(yFormatter)
  ax2.axis([1995,2011,None,None])
  
  legend([p1],['Sample Size'], loc=2)
  show()  
  
def median_cost_vs_age( ax = fig.add_subplot(1,1,1), to_show=True):
  fig.suptitle("Asking Price Distribution by Age", fontsize=18, weight='bold')
  
  session = Session()
  
  q = session.query(Listing).filter(Listing.year_built != None).filter(Listing.price != None)
  total = q.count()
  trim = int( total * .01 )
  first_date = q.order_by(asc(Listing.year_built))[trim].year_built
  last_date = q.order_by(desc(Listing.year_built)).first().year_built
  step = int((last_date - first_date)/12. )
  
  def prices(start,end):
    return [ x.price for x in q.filter('listing.year_built >= %s' % start).filter('listing.year_built < %s' % end).all() ]
    
  X = arange(first_date, last_date, step)
  Y = [ prices(x,x+step) for x in X ]
  C = [ len(y) for y in Y ]
  

  ax.set_title("Boxes show median and quartiles, lines show inner quartile range")   
  ax.set_xlabel("Year Built")
  p1=ax.plot(X,C,'--k', alpha=.5, zorder=-1)
  ax.set_ylabel('Sample Size')
  
  ax2 = ax.twinx() 
  ax2.boxplot(Y, sym='', whis=1.5, positions=X, widths=(.5*step))
  ax2.set_ylabel("Asking Price Distribution ($)")
  ax2.grid(True)
  ax2.axis([first_date-(step/2),last_date,None,None])
  ax2.yaxis.set_major_formatter(mFormatter)
  ax2.xaxis.set_major_formatter(yFormatter)
  
  legend([p1],['Sample Size'], loc=2)
  show()  

def sale_size_distribution( ax = fig.add_subplot(1,1,1), to_show = True):
  fig.suptitle("Home Size Distribution", fontsize=18, weight='bold')
  
  session = Session()
  
  area_query = session.query(Listing).filter(Listing.size != None)
  total = area_query.count()
  trim = int( total * .02 )
  max_area = area_query.order_by(desc(Listing.size))[trim].size
  min_area = area_query.order_by(asc(Listing.size)).first().size
  step = int( (max_area - min_area)/100.0 )
  
  X = arange(min_area, max_area, step)
  Y = [ area_query.filter("listing.size >= %s" % str(x)).filter("listing.size < %s" % str(x+step)).count() for x in X ]
  C = [ 100*float(area_query.filter("listing.size < %s" % str(x+step)).count())/total for x in X ]
  
  ax.bar(X,Y, width=step, color='c',edgecolor='c')
  
  ax.set_ylabel("Units Available")
  ax.set_xlabel("Size (sf)")
  
  ax2 = ax.twinx()
  ax2.plot(X,C,'--k')
  ax2.set_ylabel('Cumulative Units (%)')
  ax2.axis([min_area,max_area,None,None])
  
  show()
  
def rent_per_sf_distribution( ax = fig.add_subplot(1,1,1), to_show = True ):
  fig.suptitle("Rent/sf Distribution", fontsize=18, weight='bold')
  session = Session()

  per_sf_query = session.query(Rental).filter(Rental.price != None).filter(Rental.size != None).order_by(asc(Rental.price / Rental.size))
  total_rentals = per_sf_query.count()
  trim = int( per_sf_query.count() * .01 )
  per_sf_min = float( per_sf_query.first().price / per_sf_query.first().size )
  per_sf_query = session.query(Rental).filter(Rental.price != None).filter(Rental.size != None).order_by(desc(Rental.price / Rental.size))
  per_sf_max = float( per_sf_query[trim].price / per_sf_query[trim].size )

  step = float( (per_sf_max-per_sf_min)/100.0 )
  print [per_sf_max,per_sf_min,step]

  X = arange(per_sf_min, per_sf_max, step)
  Y = [ per_sf_query.filter("rental.price / rental.size >= %s" % x).filter("rental.price / rental.size < %s" % (x + step)).count() for x in X ]
  C = array( [ per_sf_query.filter("rental.price / rental.size < %s" % (x + step)).count() for x in X ] )
    
  ax.bar(X,Y, width=step, color='y', edgecolor='y')
  
  ax.set_ylabel("Units Available")
  ax.set_xlabel("Monthly Rent / sf ($/sf)")
  
  ax2 = ax.twinx()
  ax2.plot(X,C,'--k')
  ax2.set_ylabel('Cumulative Units (%)')
  ax2.axis([per_sf_min,per_sf_max,None,None])
    
  show()
  
def cost_per_sf_distribution( ax = fig.add_subplot(1,1,1), to_show = True ):
  fig.suptitle("Home Price/sf Distribution", fontsize=18, weight='bold')
  session = Session()

  per_sf_query = session.query(Listing).filter(Listing.price != None).filter(Listing.size != None).order_by(asc(Listing.price / Listing.size))
  trim = int( per_sf_query.count() * .01 )
  per_sf_min = int( per_sf_query.first().price / per_sf_query.first().size )
  per_sf_query = session.query(Listing).filter(Listing.price != None).filter(Listing.size != None).order_by(desc(Listing.price / Listing.size))
  per_sf_max = int( per_sf_query[trim].price / per_sf_query[trim].size )

  step = int( (per_sf_max-per_sf_min)/100.0 )

  X = arange(per_sf_min, per_sf_max, step)
  Y = [ per_sf_query.filter("listing.price / listing.size >= %s" % x).filter("listing.price / listing.size < %s" % (x + step)).count() for x in X ]
  C = [ per_sf_query.filter("listing.price / listing.size < %s" % (x + step)).count() for x in X ]
  
  ax.bar(X,Y, width=step, color='y', edgecolor='y')
  
  ax.set_ylabel("Units Available")
  ax.set_xlabel("Asking Price / sf ($/sf)")
  
  ax2 = ax.twinx()
  ax2.plot(X,C,'--k')
  ax2.set_ylabel('Cumulative Units')
  ax2.axis([per_sf_min,per_sf_max,None,None])
    
  show()

def sale_price_distribution( ax = fig.add_subplot(1,1,1), to_show = True ):
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
  
def rental_price_distribution( ax = fig.add_subplot(1,1,1), to_show = True ):
  fig.suptitle("Rental Availability by Price", fontsize=18, weight='bold')
  session = Session()
  
  trim = int(session.query(Rental).count()/50.0)
  price_max = int( session.query(Rental).filter(Rental.price != None).order_by(-Rental.price)[trim].price )
  price_min = int( session.query(Rental).filter(Rental.price != None).order_by(Rental.price)[trim].price )
  step = int( (price_max-price_min)/100.0 )

  X = range(price_min, price_max, step)
  Y = [ session.query(Rental).filter(Rental.price >= x).filter(Rental.price < x+step).count() for x in X ]
  C = [ session.query(Rental).filter(Rental.price < x).count() for x in X ]
    
  ax.bar(X,Y, width=step, color='g', edgecolor='g')
  ax.set_ylabel("Units Available")
  ax.set_xlabel("Monthly Rent ($)")
  ax.grid(True)
  ax.axis([price_min,price_max,None,None])

  ax2 = ax.twinx()
  ax2.plot(X,C,'--k')
  ax2.set_ylabel('Cumulative Units')
  ax2.axis([price_min,price_max,None,None])
  
  if to_show:
    show()

def help():
  print __doc__
  return 0
	
def process(arg='run'):
  if arg in _Functions:
    globals()[arg]()
	
class Usage(Exception):
  def __init__(self, msg):
    self.msg = msg

def main(argv=None):
  if argv is None:
    argv = sys.argv
  try:
	  try:
		  opts, args = getopt.getopt(sys.argv[1:], "hl:d:", ["help","list=","database="])
	  except getopt.error, msg:
		  raise Usage(msg)
	
	  # process options
	  for o, a in opts:
		  if o in ("-h", "--help"):
			  for f in _Functions:
				  if f in args:
					  apply(f,(opts,args))
					  return 0
			  help()
	
	  # process arguments
	  for arg in args:
		  process(arg) # process() is defined elsewhere
  except Usage, err:
	  print >>sys.stderr, err.msg
	  print >>sys.stderr, "for help use --help"
	  return 2

if __name__ == "__main__":
  sys.exit(main())
