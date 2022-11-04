
import os
import sys
import time
import json


src_path = os.path.join(os.path.dirname(__file__), "..")
sys.path.append(src_path)

from common.retailers import Retailer
from common import clean_price, clean_title,find_between_string
from scraper import post_page,get_page_soup,get_page
from scraper.base_scraper import BaseScraper, main

import logging
from common import config
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)

class DiscountbanditScraper(BaseScraper):
    """Discountbandit spider."""
    retailer = Retailer.DISCOUNTBANDIT
    name = "discountbandit_spider"
    base_url = 'https://www.discountbandit.com{}'
    allowed_domain = "www.discountbandit.com"
    custom_settings = {
        'CRAWLERA_ENABLED': 'True',
        'HTTPERROR_ALLOWED_CODES': [400, 404, 403,503],
        'ROBOTSTXT_OBEY': 'False',
    }

    def homepage_soup(self):
        soup = get_page_soup("https://www.discountbandit.com/",use_proxy=True)

        self.get_category_urls(soup)

    def get_category_urls(self, response):
        a=[]
        """get category urls from top nav bar"""
        cat = response.findAll("li", class_="CmsBlock small-12 columns")
        for category in cat:
            links = category.find('a')['href']
            link = self.base_url.format(links) if 'https' not in links else links
            soup=get_page_soup(link)
            self.listpage_details((soup))
        # for each in a[0:1]:
        #     print(each)
        #     soup = get_page_soup(each)
        #     self.listpage_details(soup)


    def listpage_details(self, response):
        products = response.findAll('div',class_="ProductMiniBuyBoxCmsBlock_sections small")

        try:
            if products:
                for product in products:
                    item = {}

                    title = product.find('img', class_="ProductMiniBuyBoxCmsBlock_product_image")['alt']
                    item['title'] = title if title else None

                    brand = product.find('span',{'class' :"ProductMiniBuyBoxCmsBlock_brand_name"})
                    item['brand'] = brand.text if brand else None

                    prod_url = product.find('div',class_="ProductMiniBuyBoxCmsBlock_image_section")
                    product_url = prod_url.find('a')['href']
                    formated_url = self.base_url.format(product_url) if product_url and 'https' not in product_url else product_url
                    item['product_url'] = clean_title(formated_url) if product_url else None

                    item['sku'] = product.find(['unbxdparam_sku'])

                    image_url = product.find('img',class_="ProductMiniBuyBoxCmsBlock_product_image")['src']
                    item['image_url'] = 'https:' + image_url if image_url and 'https' not in image_url else image_url

                    list_price_list = product.find('div',class_="ProductMiniBuyBoxCmsBlock_old_price")
                    list_price = list_price_list.text[17:] if list_price_list else None
                    item['list_price']=list_price

                    offer_price = product.find('div',class_="ProductMiniBuyBoxCmsBlock_price")
                    offerprice=offer_price.text[19:] if offer_price else None
                    item['offer_price'] = clean_price(offerprice)
                    #print(item)

                    soup = get_page_soup(formated_url)
                    self.productpage_details(soup,item,formated_url)

        except Exception as e:
            logger.error('error in listpage detail:{}'.format(e))

        try:

            max_page = self.max_pages if self.max_pages > 0 else True
            if self.page_no < max_page - 1:
                self.page_no += 1
                next_page = response.find('a', {'aria-label': 'Go to next page'})['href']
                if next_page:
                    print("next page", next_page)
                    next_page_response = get_page_soup(next_page, use_proxy=True)
                    self.listpage_details(next_page_response)
        except Exception as e:
            logger.error('error in pagination: {}'.format(e))


    def productpage_details(self,response,item,formated_url):

        try:
            title = response.find('h1').text
            item['title'] = title if title else item.get('title')
            item['title'] = clean_title(title) if title else item.get('title')

            list_price = response.find('span',class_="ProductBuyBoxCmsBlock_pricing_display_list_price")
            price = list_price.text[22:]
            item['list_price'] = clean_price(price) if price else item.get('list_price')

            offer_price = response.find('span', class_="ProductBuyBoxCmsBlock_pricing_display_product_price")
            offerprice = offer_price.text
            item['offer_price'] = clean_price(offerprice.split('Sale: ')[1]) if offer_price else item.get('offer_price')

            availability = response.find('span', class_="ProductBuyBoxCmsBlock_stock_and_shipping_status__stock")
            available=availability.text
            if available:
                item['out_of_stock']  = False if 'in stock' in available.lower() else True

            else:
                item['available'] = None

            image_urls = response.find('div',class_="ProductMediaGalleryCmsBlock_main_flexbox")
            imageurl1=image_urls.find('img')['src'] if image_urls else None
            imageurl2 = imageurl1 if imageurl1 else item.get('image_url')
            item['image_url'] =imageurl2
            # if imageurl2:
            #     finding_upc = find_between_string(imageurl2, "products/", ".jpg")
            #     upc = finding_upc[-14:]
            #     item['upc'] =upc if finding_upc else None
            # else:
            #     item['upc'] =None


            description_list = [clean_title(each.text) for each in response.find('div',
                                                                                 class_="CmsBlock ProductPage_ProductOverview small-12 medium-8 columns").findAll(
                'p') if each and each.text and clean_title(each.text)]

            descriptionlist = ", ".join(description_list) if description_list else None

            item['description'] = clean_title(descriptionlist.replace('\xa0','')) if descriptionlist and '\xa0' in descriptionlist else descriptionlist if descriptionlist else None

            mpn = response.find('div',{"class": "ProductPageHeaderCmsBlock_model_and_sku"})
            mpn_data=mpn.find('span').find('strong') if mpn and mpn.find('span') and mpn.find('span').find('strong') else None
            if mpn_data:
                item['mpn'] = mpn_data.text if mpn_data else None
            else:
                mpn1 = response.find("div", {"data-ct": "ProductSpecificationsCmsBlock"}).findAll('tr')
                mpn1_data = [each for each in mpn1 if
                               each.find('th', {'scope': 'row'}) and each.find('th', {'scope': 'row'}).find(
                                   'strong') and each.find('th', {'scope': 'row'}).find(
                                   'strong').text and 'part number' in each.find('th', {'scope': 'row'}).find(
                                   'strong').text.lower()]
                if mpn1_data:
                    mpn1data=mpn1_data[0].find('td').text
                    clean_mpn= clean_title(mpn1data)
                    item['mpn'] =clean_mpn if mpn1data else None

            upc = response.find("div", {"data-ct": "ProductSpecificationsCmsBlock"}).findAll('tr')
            upc_data = [each for each in upc if
                         each.find('th', {'scope': 'row'}) and each.find('th', {'scope': 'row'}).find(
                             'strong') and each.find('th', {'scope': 'row'}).find(
                             'strong').text and 'gtin' in each.find('th', {'scope': 'row'}).find(
                             'strong').text.lower()]
            if upc_data:
                upc1data = upc_data[0].find('td').text
                clean_upc= clean_title(upc1data)
                item['upc'] = clean_upc if upc1data else None

            sku = response.find('div',{"class": "ProductPageHeaderCmsBlock_row"})['data-product-sku']
            if sku:
                item['sku'] = sku if sku else item.get('sku')
            else:
                sku1=response.find("div", {"data-ct": "ProductSpecificationsCmsBlock"}).findAll('tr')
                sku1_data = [each for each in sku1.find('td').text for each in sku1 if
                               each.find('th', {'scope': 'row'}) and each.find('th', {'scope': 'row'}).find(
                                   'strong') and each.find('th', {'scope': 'row'}).find(
                                   'strong').text and 'gtin' in each.find('th', {'scope': 'row'}).find(
                                   'strong').text.lower()]
                if sku1_data:
                    sku1data= sku1_data[0].find('td').text
                    cleansku = clean_title(sku1data)
                    item['mpn'] = cleansku if sku1data else None

            category =  response.find('div',{'data-ct':"BreadCrumbsCmsBlock"}).text
            cat=category[4:]
            if category:
                item['category'] = ' Home > {} '.format(cat)
            else:
                item['category'] = 'Home > {}'.format(item['title'])

            try:
                if 'women' in item['category'].lower() or 'women' in item['title'].lower() \
                        or 'women' in item['product_url'].lower():
                    item['gender'] = 'female'
                    item['age'] = 'adult'
                elif 'girls' in item['category'].lower() or 'girls' in item['title'].lower() or 'girls' \
                        in item['product_url'].lower():
                    item['gender'] = 'female'
                    item['age'] = 'kids'
                elif 'mens' in item['category'].lower() or 'mens' in item['title'].lower() or 'mens' \
                        in item['product_url'].lower():
                    item['gender'] = 'male'
                    item['age'] = 'adult'
                elif 'boys' in item['category'].lower() or 'boys' in item['title'].lower() or 'boys' in \
                        item['product_url'].lower():
                    item['gender'] = 'male'
                    item['age'] = 'kids'
                elif 'unisex' in item['category'].lower() or 'unisex' in item['title'].lower() or \
                        'unisex' in item['product_url'].lower():
                    item['gender'] = 'unisex'
            except Exception as e:
                logger.error('error found:',e)

            try:
                if item['category'] and item['title'] and item['description']:
                    if 'adult' in item['category'].lower() or 'adult' in item['title'].lower() or 'adult' in \
                            item['description'].lower():
                        item['age'] = 'adult'
                    elif 'kids' in item['category'].lower() or 'kids' in item['title'].lower() or 'kids' in \
                            item['description'].lower():
                        item['age'] = 'kids'

                else:
                    item['age'] = None
                print(item)
                self.all_products.append(item)
            except Exception as e:
                logger.error('error in product detail', e,formated_url)

        except Exception as e:
            logger.error('error in productpage', e, response.url)




    def main(self):
        self.page_no = 0
        self.all_products = []
        self.homepage_soup()
        self.max_pages = self.parse_args().pages

        if self.all_products:
            full_file_path = os.path.join(self.feed_dir, '%s.jl' % self.retailer.value)
            self.store_products_to_file(self.all_products, full_file_path)
if __name__ == '__main__':
    main(DiscountbanditScraper, Retailer.DISCOUNTBANDIT)

