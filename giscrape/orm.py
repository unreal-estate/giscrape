import re
from datetime import *

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import *
from sqlalchemy.orm.interfaces import *
from geoalchemy import *

engine = create_engine('postgresql://postgres:kundera2747@localhost/gisdb', echo=True)
metadata = MetaData(engine)
Base = declarative_base(metadata=metadata)
Session = sessionmaker(bind=engine)
global DefaultDialect
DefaultDialect = engine.dialect

class Fail(StandardError):
  pass
     
class PropertyHistory(Base):
  __tablename__ = 'property_history'
  __table_args__ = {'schema':'gis_schema'}
  
  id = Column(Integer, primary_key=True, index=True)
  property_id = Column(Integer, ForeignKey('gis_schema.property.id'))
  
  status = Column(String)
  price = Column(Float, index=True)
  date = Column(DateTime)
  
class Property(Base):
  __tablename__ = 'property'
  __table_args__ = {'schema':'gis_schema'}
  
  discriminator = Column('type', String(50), index=True) 
  __mapper_args__ = {'polymorphic_on': discriminator}
    
  id = Column(Integer, primary_key=True, index=True)
  url = Column(String, index=True)
  address = Column(String)

  bedrooms =      Column(Integer, nullable=True, index=True)
  bathrooms =     Column(Float, nullable=True, index=True)
  powder_rooms =  Column(Integer, nullable=True, index=True) 
  property_type = Column(String, nullable=True, index=True)
  size =          Column(Integer, nullable=True, index=True)
  lot =           Column(Integer, nullable=True)
  year_built =    Column(Integer, nullable=True, index=True)
  date_listed =   Column(Date, nullable=True, index=True,)
  mls_id =        Column(String, nullable=True)

  descriptive_title = Column(String, nullable=True)
  description =       Column(String, nullable=True)

  additional_fields = Column(String, nullable=True)

  public_records =    Column(String, nullable=True)

  lat = Column(Float, nullable=True, index=True)
  lon = Column(Float, nullable=True, index=True)
  geom = GeometryColumn(Point(2,2277), nullable=True)

  last_crawl = Column(DateTime)

  #tcad_2008_id = Column(Integer, ForeignKey('gis_schema.2008 TCAD Parcels.gid'))
  tcad_2008_id = Column(Integer, ForeignKey('gis_schema.2008 TCAD Parcels.gid'))
  tcad_2008_parcel = relationship("TCAD_2008", backref="rentals")  
  
  historical_values = relation("PropertyHistory", backref="property")
  
  @property
  def identity(self):
    return self.url
    
  @validates('bedrooms', 'bathrooms', 'powder_rooms', 'property_type', 'size', 'lot', 'year_built', 'date_listed', 'mls_id')
  def validate_not_dash(self, key, value):
    if value == '\xe2': return None
    return value
    
  @validates('date_listed')
  def validate_date(self, key, value):
    if (value == '180+ days ago'):
      return None 
    elif re.search('(\d+) days ago'):
      return datetime.now() - timedelta( int( re.findall('(\d+) days ago', value)[0] ) )
    else:
      return datetime.strptime(value.replace('st','').replace('nd','').replace('rd','').replace('th',''),'%b %d, %Y')

  @validates('size')
  def validate_number(self, key, value):
    return value.replace(',','').strip('$')
    
  @validates('lot')
  def validate_area(self, key, value):
    by_sf = re.compile(r'([\d|,]+) sqft')
    by_acre = re.compile(r'([\d|,|.]+) acres')
    if by_sf.search(value):
      return by_sf.findall(value)[0].replace(',','')
    elif by_acre.search(value):
      return int( 43560.0 * float( by_acre.findall(value)[0].replace(',','') ) )
    
  @validates('address')
  def validate_address(self, key, value):
    if 'Address Not Disclosed' in value: return None
    return value
    
  def validate_cost(self, key, value):
    if re.search(r'\xe2', value) or value.count(u'\u2013'): raise Fail, "Price span"
    
    return re.findall(r'\$([\d|,]+)', value)[0].replace(',','').strip('$')
    
  @validates('description', 'additional_fields', 'public_records')
  def validate_paragraph(self, key, value):
    return reduce(lambda x, y: x+y, value) if isinstance(value, list) else value
    
#context_listing = Table('context_listing', Base.metadata,
    #Column('context_id', Integer, ForeignKey('gis_schema.context.id')),
    #Column('listing_id', Integer, ForeignKey('gis_schema.listing.id')),
#    Column('context_id', Integer, ForeignKey('gis_schema.context.id')),
#    Column('listing_id', String, ForeignKey('gis_schema.listing.url')),
    #schema = 'gis_schema', 
#    useexisting=True
#)
#context_rental = Table('context_rental', Base.metadata,
    #Column('context_id', Integer, ForeignKey('gis_schema.context.id')),
    #Column('rental_id', Integer, ForeignKey('gis_schema.rental.id')),
#    Column('context_id', Integer, ForeignKey('gis_schema.context.id')),
#    Column('rental_id', String, ForeignKey('gis_schema.rental.url')),
    #schema = 'gis_schema', 
#    useexisting=True
#)

class Rental(Property):
  __tablename__ = 'rental'
  __table_args__ = {'schema':'gis_schema'}
  __mapper_args__ = {'polymorphic_identity': 'rental'}
  
  id = Column(Integer, ForeignKey('gis_schema.property.id'), primary_key=True)
  
  rent =          Column(Float, index=True)
  price_period =  Column(String, nullable=True)
  lease_term =    Column(String, nullable=True)
  pets_allowed =  Column(String, nullable=True)

  #contexts = relationship("Context", secondary=context_rental)
  
  @property
  def identity(self):
    return self.url
    
  @validates('rent', 'price_period', 'lease_term', 'pets_allowed')
  def rental_validate_not_dash(self, key, value):
    return self.validate_not_dash(key,value)
  
  @validates('rent')
  def rental_validate_cost(self,key,value):
    return self.validate_cost(key,value)
    
class Listing(Property):
  __tablename__ = 'listing'
  __table_args__ = {'schema':'gis_schema'}
  __mapper_args__ = {'polymorphic_identity': 'listing'}

  id = Column(Integer, ForeignKey('gis_schema.property.id'), primary_key=True, index=True)
  
  price       = Column(Float, index=True)
  sale_price  = Column(Integer, nullable=True, index=True)
  sale_date   = Column(Date, nullable=True)
  
  #contexts = relationship("Context", secondary=context_listing)  
  
  @property
  def identity(self):
    return self.id
    
  @validates('price', 'sale_price', 'sale_date')
  def listing_validate_not_dash(self, key, value):
    return self.validate_not_dash(key, value)
  
  @validates('price', 'sale_price')
  def listing_validate_cost(self, key, value):
    return self.validate_cost(key, value)
  
  @validates('sale_date')
  def listing_validate_date(self, key, value):
    return self.validate_date(key, value)
  
  @validates('price_per_sf')
  def listing_validate_number(self, key, value):
    return self.validate_number(key, value)

class Context(Base):
  __tablename__ = 'context'
  __table_args__ = {'schema':'gis_schema'}
  
  id = Column(Integer, primary_key=True)
  
  name = Column(String, unique=True, index=True)

  geom = GeometryColumn(Polygon(2, srid=2277))
  
  #listings = relationship("Listing", secondary=context_listing)
  #rentals = relationship("Rental", secondary=context_rental)  
                    
  def cache_contents(self,session):
    self.listings = []
    self.listings = session.query(Listing).filter(Listing.geom != None).filter( Listing.geom.transform(2277).within(self.geom.transform(2277))).all()
    
    self.rentals = []
    self.rentals = session.query(Rental).filter(Rental.geom != None).filter( Rental.geom.transform(2277).within(self.geom.transform(2277))).all()
    
    self.sales = []
    self.rentals = session.query(Sale).filter(Sale.geom != None).filter( Sale.geom.transform(2277).within(self.geom.transform(2277))).all()

class TCAD_2008(Base):
  __tablename__ = '2008 TCAD Parcels'
  __table_args__ = {'schema':'gis_schema'}  
  
  gid           = Column(Integer, primary_key=True)
  acreage       = Column(Float, nullable=True)
  roads         = Column(String, nullable=True)
  water         = Column(String, nullable=True)
  ag_land       = Column(String, nullable=True)
  vli_2005      = Column(String, nullable=True)
  vli_2008      = Column(String, nullable=True)
  pct_impr      = Column(String, nullable=True)
  geo_id        = Column(String, nullable=True)
  land_state    = Column(String, nullable=True)
  marketvalu    = Column(Integer, nullable=True)
  shape_leng    = Column(Numeric, nullable=True)
  shape_area    = Column(Numeric, nullable=True)
  improvemen    = Column(Integer, nullable=True)
  land_value    = Column(Integer, nullable=True)
  value_per_acre= Column(Integer, nullable=True)
  the_geom      = GeometryColumn(Polygon(2, srid=2277 ))
  
  @property
  def identity(self):
    return self.gid
    

class Person(Base):
  __tablename__ = 'person'
  __table_args__ = {'schema':'gis_schema'}
  
  id = Column(Integer, primary_key=True)
  
  first_name = Column(String, nullable=True)
  middle_name = Column(String, nullable=True)
  last_name = Column(String, nullable=True)
  city = Column(String, nullable=True)
  state = Column(String, nullable=True)
  zipcode = Column(String, nullable=True)
  
  cities = Column(String, nullable=True)
  birth_year = Column(Integer, nullable=True)
  job_title = Column(String, nullable=True)
  employer = Column(String, nullable=True)
  
  owned_properties = relation("TCAD_2010", backref="person")
  
  @validates('birth_year')
  def validate_number(self, key, value):
    if isinstance(value, list):
      value = value[0]
    if isinstance(value, str) or isinstance(value, unicode):
      value = value.replace(',','').strip()
    
    return float( value ) if value else None
    
  @validates('first_name', 'last_name', 'city', 'state', 'zipcode', 'middle_name', 'job_title', 'employer')
  def validate_string(self, key, value):
    if isinstance(value, list):
      value = reduce(lambda x, y: x+y, value)
    value = value.strip()
    
    return value

  @validates('cities')
  def validate_list(self, key, value):
    return reduce(lambda x, y: "%s:%s" % (x,y), value)
    
class TCAD_2010(Base):
  __tablename__ = '2010 TCAD Parcels'
  __table_args__ = {'schema':'gis_schema'}  
  
  gid       = Column(Integer)

  objectid  = Column(Integer, primary_key=True, nullable=True)
  area      = Column(Numeric, nullable=True)
  plat      = Column(String, nullable=True)
  pid_10    = Column(String, nullable=True)   #TCAD Ref
  prop_id   = Column(Integer, nullable=True)  #TCAD ID
  lots      = Column(String, nullable=True)
  situs     = Column(String, nullable=True)   #Address Number
  blocks    = Column(String, nullable=True)
  condoid   = Column(String, nullable=True)
  condoid2  = Column(String, nullable=True)
  parcel_blo= Column(String, nullable=True)
  nbhd      = Column(String, nullable=True)
  zoning    = Column(String, nullable=True)
  land_value= Column(Numeric, nullable=True)
  grid      = Column(String, nullable=True)
  wcid17    = Column(String, nullable=True)
  shape_area= Column(Numeric, nullable=True)
  shape_len = Column(Numeric, nullable=True)
  the_geom  = GeometryColumn(Polygon(2, srid=2277 ))
  

  # Additional fields from TCAD scrape
  url               = Column(String, nullable=True)

  owner             = Column(String, nullable=True)
  owner_address     = Column(String, nullable=True)
  address           = Column(String, nullable=True)
  improvement_value = Column(Numeric, nullable=True)
  market_value      = Column(Numeric, nullable=True)
  acreage           = Column(Float, nullable=True)
  neighborhood      = Column(String, nullable=True)
  improvement_area  = Column(Numeric, nullable=True)
  
  improvements = relation("TCADImprovement", backref="parcel")
  historical_values = relation("TCADValueHistory", backref="parcel")
  
  person_id = Column(Integer, ForeignKey('gis_schema.person.id'))

  last_crawl = Column(DateTime)
  
  @property
  def identity(self):
    return self.prop_id
    
  @validates('prop_id', 'objectid', 'land_value', 'improvement_value', 'market_value', 'acreage', 'improvement_area')
  def validate_number(self, key, value):
    if isinstance(value, list):
      value = value[0]
    if isinstance(value, str) or isinstance(value, unicode):
      value = value.replace(',','').strip()
    
    return float( value ) if value else None
    
  @validates('url', 'owner', 'neighborhood', 'address')
  def validate_string(self, key, value):
    if isinstance(value, list):
      value = reduce(lambda x, y: x+y, value)
    value = value.strip()
    
    return value
    
  @validates('owner_address')
  def validate_paragraph(self, key, value):
    if isinstance(value, list):
      value = reduce(lambda x, y: x+y, value)
    value = value.replace('\t', '').strip()
    
    return value

  #@validates('improvements')
  #def validate_improvements(self, key, value):
  #  if isinstance(value, list) and not isinstance(value, TCADImprovement):
  #    value = [TCADImprovement(**x) for x in value]
  #  
  #  return value
    
class TCADImprovement(Base):
  __tablename__ = 'TCAD_improvement'
  __table_args__ = {'schema':'gis_schema'}
  
  id = Column(Integer, primary_key=True)

  parcel_id = Column(Integer, ForeignKey('gis_schema.2010 TCAD Parcels.objectid'))
    
  state_category    = Column(String, nullable=True)
  description       = Column(String, nullable=True)
  
  segments = relation("TCADSegment", backref="improvement")
  
  @validates('id', 'parcel_id')
  def validate_number(self, key, value):
    if isinstance(value, list):
      value = value[0]
    if isinstance(value, str) or isinstance(value, unicode):
      value = value.replace(',','').strip()
    
    return float( value ) if value else None
    
  @validates('state_category', 'description')
  def validate_string(self, key, value):
    if isinstance(value, list):
      value = reduce(lambda x, y: x+y, value)
    value = value.strip()
    
    return value
    
class TCADSegment(Base):
  __tablename__ = 'TCAD_segment'
  __table_args__ = {'schema':'gis_schema'}
  
  id = Column(Integer, primary_key=True)
  
  improvement_id = Column(Integer, ForeignKey('gis_schema.TCAD_improvement.id')) 
  
  type_code         = Column(String, nullable=True)
  description       = Column(String, nullable=True)
  klass             = Column(String, nullable=True)
  year_built        = Column(Integer, nullable=True)
  area              = Column(Integer, nullable=True)
  
  @validates('type_code', 'description', 'klass')
  def validate_string(self, key, value):
    if isinstance(value, list):
      value = reduce(lambda x, y: x+y, value)
    value = value.strip()
    
    return value
    
  @validates('id','improvement_id','year_built', 'area')
  def validate_number(self, key, value):
    cache = value
    if isinstance(value, list):
      value = value[0]
    if isinstance(value, str) or isinstance(value, unicode):
      value = value.replace(',','').strip()
    
    return float( value ) if value else None
    
class TCADValueHistory(Base):
  __tablename__ = 'TCAD_value_history'
  __table_args__ = {'schema':'gis_schema'}
  
  id = Column(Integer, primary_key=True)
  
  parcel_id = Column(Integer, ForeignKey('gis_schema.2010 TCAD Parcels.objectid'))
  
  year              = Column(Integer, nullable=True)
  value             = Column(Numeric, nullable=True)
  area              = Column(Numeric, nullable=True)
  new_construction  = Column(Boolean, nullable=True)
  new_checked       = Column(Boolean, nullable=True)
  
  @validates('year', 'value')
  def validate_number(self, key, value):
    if isinstance(value, list):
      value = value[0]
    if isinstance(value, str) or isinstance(value, unicode):
      value = value.replace(',','').strip()
    
    return float( value )
    
class TravelTimePoint(Base):
  __tablename__ = 'travel_distance'
  __table_args__ = {'schema':'gis_schema'}
  
  id               = Column(Integer, primary_key=True)
  
  pointnum          = Column(String, nullable=True)
  accumdst          = Column(Numeric, nullable=True)
  #gid               = Column(Numeric, nullable=True)
  prefix_dir        = Column(String, nullable=True)
  pre_type          = Column(String, nullable=True)
  street_nam        = Column(String, nullable=True)
  street_typ        = Column(String, nullable=True)
  suffix_dir        = Column(String, nullable=True)
  full_stree        = Column(String, nullable=True)
  map_grid          = Column(String, nullable=True)
  built_date        = Column(String, nullable=True)
  modified_u        = Column(String, nullable=True)
  modified_d        = Column(String, nullable=True)
  elevation_        = Column(Numeric, nullable=True)
  elevation1        = Column(Numeric, nullable=True)
  miles             = Column(Numeric, nullable=True)
  seconds           = Column(Numeric, nullable=True)
  one_way           = Column(String, nullable=True)
  action_cod        = Column(String, nullable=True)
  input_date        = Column(String, nullable=True)
  input_uid         = Column(String, nullable=True)
  pre_dir           = Column(String, nullable=True)
  str_name          = Column(String, nullable=True)
  full_name         = Column(String, nullable=True)
  suf_dir           = Column(String, nullable=True)
  shape_len         = Column(Numeric, nullable=True)
  speed_limit       = Column(Integer, nullable=True, index=True)
  redundant_checked = Column(Boolean, default=False)
  
  radius_100        = Column(Boolean, default=None, nullable=True)
  radius_1000       = Column(Boolean, default=None, nullable=True)
  radius_5000       = Column(Boolean, default=None, nullable=True)

  geom              = GeometryColumn(Point(2, srid=2277))
  
  times             = relation("TravelTime", backref='destination', cascade="all, delete, delete-orphan")
  
class TravelTime(Base):
  __tablename__ = 'travel_time'
  __table_args__ = {'schema':'gis_schema'}
  
  id               = Column(Integer, primary_key=True)
  
  duration      = Column(Integer)   # Travel time from origin to destination in minutes
  mode          = Column(String)
  origin        = Column(String)
  destination_id= Column(Integer, ForeignKey('gis_schema.travel_distance.id'))
  
  
GeometryDDL(Property.__table__)
GeometryDDL(Context.__table__)
GeometryDDL(TCAD_2008.__table__)
GeometryDDL(TCAD_2010.__table__)
