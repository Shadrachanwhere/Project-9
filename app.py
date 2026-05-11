from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base, sessionmaker
import csv
import datetime
import shutil

# Create SQLite database engine
engine = create_engine('sqlite:///inventory.db')

# Create base class for models
Base = declarative_base()


# Define Brand model
class Brand(Base):
    __tablename__ = 'brands'
    brand_id = Column(Integer, primary_key=True)
    brand_name = Column(String, nullable=False, unique=True)


def get_or_create_brand(session, brand_name):
    normalized_name = brand_name.strip()
    if not normalized_name:
        return None

    brand = session.query(Brand).filter(func.lower(Brand.brand_name) == normalized_name.lower()).first()
    if brand:
        return brand

    brand = Brand(brand_name=normalized_name)
    session.add(brand)
    session.flush()
    return brand


# Define Product model
class Product(Base):
    __tablename__ = 'products'
    
    product_id = Column(Integer, primary_key=True)
    product_name = Column(String, nullable=False)
    product_quantity = Column(Integer, nullable=False)
    product_price = Column(Float, nullable=False)
    date_updated = Column(DateTime, nullable=False)
    brand_id = Column(Integer, ForeignKey('brands.brand_id'), nullable=False)


# Create session factory
Session = sessionmaker(bind=engine)        


def view_product_details():
    session = Session()
    products = session.query(Product).order_by(Product.product_id).all()

    if not products:
        print('No products available.')
        session.close()
        return

    print('\nAvailable products:')
    for product in products:
        print(f"{product.product_id}: {product.product_name}")

    while True:
        user_input = input('\nEnter product ID to view, or type Q to return: ').strip()
        if user_input.upper() == 'Q':
            print('Returning to the main menu.')
            session.close()
            return

        try:
            product_id = int(user_input)
        except ValueError:
            print('Invalid entry. Please enter a numeric product ID or Q to quit.')
            continue

        product = session.query(Product).filter_by(product_id=product_id).first()
        if not product:
            print(f'No product with ID {product_id} found. Please try again.')
            continue

        while True:
            brand = session.query(Brand).filter_by(brand_id=product.brand_id).first()
            brand_name = brand.brand_name if brand else 'Unknown'

            print('\nProduct details:')
            print('Product ID:', product.product_id)
            print('Name:', product.product_name)
            print('Quantity:', product.product_quantity)
            print('Price:', product.product_price)
            print('Last updated:', product.date_updated)
            print('Brand:', brand_name)

            print('\nOptions for this product:')
            print('E - Edit this product')
            print('D - Delete this product')
            print('R - Return to the main menu')

            action = input('Choose an option: ').strip().upper()
            if action == 'E':
                edit_product(session, product)
                break
            elif action == 'D':
                delete_product(session, product)
                break
            elif action == 'R':
                print('Returning to the main menu.')
                break
            else:
                print('Invalid option. Please choose E, D, or R.')
        break

    session.close()


def edit_product(session, product):
    print('\nLeave a field blank to keep the current value.')
    new_name = input(f'Product name [{product.product_name}]: ').strip()
    new_price = input(f'Product price [{product.product_price}]: ').strip()
    new_quantity = input(f'Product quantity [{product.product_quantity}]: ').strip()

    if new_name:
        product.product_name = new_name

    if new_price:
        try:
            product.product_price = float(new_price.replace('$', ''))
        except ValueError:
            print('Price not updated: invalid value.')

    if new_quantity:
        try:
            product.product_quantity = int(new_quantity)
        except ValueError:
            print('Quantity not updated: invalid value.')

    brands = session.query(Brand).order_by(Brand.brand_id).all()
    if brands:
        print('\nAvailable brands:')
        for brand in brands:
            print(f"{brand.brand_id}: {brand.brand_name}")
        print(f"Current brand ID: {product.brand_id}")

        while True:
            new_brand = input('Enter brand ID to assign, or leave blank to keep current: ').strip()
            if not new_brand:
                break
            try:
                brand_id = int(new_brand)
            except ValueError:
                print('Please enter a valid numeric brand ID or leave blank.')
                continue

            brand = session.query(Brand).filter_by(brand_id=brand_id).first()
            if brand:
                product.brand_id = brand_id
                break
            print(f'Brand ID {brand_id} not found. Please choose a valid brand ID.')
    else:
        print('No brands are available to choose from.')

    product.date_updated = datetime.datetime.now()
    session.commit()
    print('Product updated successfully.')


def delete_product(session, product):
    confirm = input(f'Are you sure you want to delete "{product.product_name}"? (Y/N): ').strip().upper()
    if confirm == 'Y':
        session.delete(product)
        session.commit()
        print('Product deleted successfully.')
    else:
        print('Delete cancelled.')


def add_new_product():
    session = Session()

    while True:
        product_name = input('Product name: ').strip()
        if not product_name:
            print('Product name cannot be empty.')
            continue

        existing_product = session.query(Product).filter_by(product_name=product_name).first()
        if existing_product:
            while True:
                choice = input(f'Product "{product_name}" already exists. Edit existing product? (Y/N): ').strip().upper()
                if choice == 'Y':
                    edit_product(session, existing_product)
                    session.close()
                    return
                if choice == 'N':
                    print('Please enter a different product name.')
                    break
                print('Invalid option. Please enter Y or N.')
            if choice == 'N':
                continue
        break

    while True:
        product_price_input = input('Product price (integer): ').strip()
        try:
            product_price = int(product_price_input)
            break
        except ValueError:
            print('Please enter a valid integer for the price.')

    while True:
        product_quantity_input = input('Product quantity (integer): ').strip()
        try:
            product_quantity = int(product_quantity_input)
            break
        except ValueError:
            print('Please enter a valid integer for the quantity.')

    date_updated = datetime.datetime.now()

    brands = session.query(Brand).order_by(Brand.brand_id).all()
    if not brands:
        print('No brands are available. Please add brands first.')
        session.close()
        return

    print('\nAvailable brands:')
    for brand in brands:
        print(f"{brand.brand_id}: {brand.brand_name}")

    while True:
        brand_id_input = input('Enter brand ID: ').strip()
        try:
            brand_id = int(brand_id_input)
        except ValueError:
            print('Please enter a valid numeric brand ID.')
            continue

        brand = session.query(Brand).filter_by(brand_id=brand_id).first()
        if not brand:
            print(f'Brand ID {brand_id} does not exist. Please choose a valid brand ID.')
            continue
        break

    product = Product(
        product_name=product_name,
        product_price=float(product_price),
        product_quantity=product_quantity,
        date_updated=date_updated,
        brand_id=brand.brand_id,
    )
    session.add(product)
    session.commit()
    print(f"Added new product: {product_name}")
    session.close()


def add_new_brand():
    session = Session()
    while True:
        brand_name = input('Brand name: ').strip()
        if not brand_name:
            print('Brand name cannot be empty.')
            continue
        existing_brand = session.query(Brand).filter(func.lower(Brand.brand_name) == brand_name.lower()).first()
        if existing_brand:
            print(f'Brand "{existing_brand.brand_name}" already exists with ID {existing_brand.brand_id}. Please try again.')
            continue
        break

    brand = Brand(brand_name=brand_name)
    session.add(brand)
    session.commit()
    print(f'Added new brand: {brand.brand_name} (ID {brand.brand_id})')
    session.close()


def add_choice():
    while True:
        print('\nAdd menu:')
        print('1 - Add a new product')
        print('2 - Add a new brand')
        print('Q - Return to the main menu')

        choice = input('Enter your choice: ').strip().upper()
        if choice == '1':
            add_new_product()
            break
        elif choice == '2':
            add_new_brand()
            break
        elif choice == 'Q':
            print('Returning to the main menu.')
            break
        else:
            print('Invalid option. Please enter 1, 2, or Q.')


def view_analysis():
    session = Session()
    total_products = session.query(Product).count()
    total_brands = session.query(Brand).count()

    most_expensive = session.query(Product).order_by(Product.product_price.desc()).first()
    least_expensive = session.query(Product).order_by(Product.product_price).first()

    brand_counts = (
        session.query(Brand.brand_name, func.count(Product.product_id).label('product_count'))
        .join(Product, Product.brand_id == Brand.brand_id)
        .group_by(Brand.brand_id)
        .order_by(func.count(Product.product_id).desc())
        .all()
    )

    print('Total brands:', total_brands)
    print('Total products:', total_products)

    if most_expensive:
        print('\nMost expensive item:')
        print('  Name:', most_expensive.product_name)
        print('  Price:', most_expensive.product_price)
        print('  Brand ID:', most_expensive.brand_id)
    else:
        print('\nMost expensive item: none')

    if least_expensive:
        print('\nLeast expensive item:')
        print('  Name:', least_expensive.product_name)
        print('  Price:', least_expensive.product_price)
        print('  Brand ID:', least_expensive.brand_id)
    else:
        print('\nLeast expensive item: none')

    if brand_counts:
        top_brand_name, top_product_count = brand_counts[0]
        print('\nBrand with the most products:')
        print('  Brand:', top_brand_name)
        print('  Product count:', top_product_count)
    else:
        print('\nBrand with the most products: none')

    session.close()


def backup_database():
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'inventory_backup_{timestamp}.db'
    shutil.copy('inventory.db', backup_name)
    print(f'Backup created: {backup_name}')


def run_interaction():
    while True:
        print('\nChoose an option:')
        print('V - View single product details')
        print('N - Add a new brand or product')
        print('A - View an analysis')
        print('B - Backup the database')
        print('Q - Quit')

        choice = input('Enter your choice: ').strip().upper()
        if choice == 'V':
            view_product_details()
        elif choice == 'N':
            add_choice()
        elif choice == 'A':
            view_analysis()
        elif choice == 'B':
            backup_database()
        elif choice == 'Q':
            print('Quitting.')
            break
        else:
            print('Invalid option. Please enter V, N, A, B, or Q.')


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("Database initialized: inventory.db")
    
    # Reset brands and import from brands.csv
    session = Session()
    session.query(Brand).delete()
    session.commit()

    with open('brands.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row.get('brand_name'):
                get_or_create_brand(session, row['brand_name'])
    session.commit()
   
    
    # Import products from inventory CSV
    with open('inventory.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            brand_name = row['brand_name']
            brand = session.query(Brand).filter(func.lower(Brand.brand_name) == brand_name.strip().lower()).first()
            if brand:
                product_name = row['product_name']
                product_price = float(row['product_price'].strip('$'))
                product_quantity = int(row['product_quantity'])
                date_updated = datetime.datetime.strptime(row['date_updated'], '%m/%d/%Y')
                
                # Check for existing product
                existing_product = session.query(Product).filter_by(product_name=product_name).first()
                if existing_product:
                    # Update if the new data is more recent
                    if date_updated > existing_product.date_updated:
                        existing_product.product_quantity = product_quantity
                        existing_product.product_price = product_price
                        existing_product.date_updated = date_updated
                        existing_product.brand_id = brand.brand_id
                        print(f"Updated existing product: {product_name}")
                else:
                    # Create new product
                    product = Product(
                        product_name=product_name,
                        product_quantity=product_quantity,
                        product_price=product_price,
                        date_updated=date_updated,
                        brand_id=brand.brand_id
                    )
                    session.add(product)
            else:
                print(f"Warning: Brand '{brand_name}' not found, skipping product '{row['product_name']}'")
    session.commit()
    print("Products imported from inventory.csv")
    session.close()

    run_interaction()


