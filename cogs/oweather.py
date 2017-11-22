from cogs.utils.dataIO import dataIO
from discord.ext import commands
from .utils import checks
import collections
import aiohttp
import discord
import os


class Weather:
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = 'data/weather/weather.json'
        self.settings = dataIO.load_json(self.settings_file)
        self.countries = {
            'Afghanistan': 'AF',
            'Albania': 'AL',
            'Algeria': 'DZ',
            'American Samoa': 'AS',
            'Andorra': 'AD',
            'Angola': 'AO',
            'Anguilla': 'AI',
            'Antarctica': 'AQ',
            'Antigua and Barbuda': 'AG',
            'Argentina': 'AR',
            'Armenia': 'AM',
            'Aruba': 'AW',
            'Australia': 'AU',
            'Austria': 'AT',
            'Azerbaijan': 'AZ',
            'Bahamas': 'BS',
            'Bahrain': 'BH',
            'Bangladesh': 'BD',
            'Barbados': 'BB',
            'Belarus': 'BY',
            'Belgium': 'BE',
            'Belize': 'BZ',
            'Benin': 'BJ',
            'Bermuda': 'BM',
            'Bhutan': 'BT',
            'Bolivia, Plurinational State of': 'BO',
            'Bonaire, Sint Eustatius and Saba': 'BQ',
            'Bosnia and Herzegovina': 'BA',
            'Botswana': 'BW',
            'Bouvet Island': 'BV',
            'Brazil': 'BR',
            'British Indian Ocean Territory': 'IO',
            'Brunei Darussalam': 'BN',
            'Bulgaria': 'BG',
            'Burkina Faso': 'BF',
            'Burundi': 'BI',
            'Cambodia': 'KH',
            'Cameroon': 'CM',
            'Canada': 'CA',
            'Cape Verde': 'CV',
            'Cayman Islands': 'KY',
            'Central African Republic': 'CF',
            'Chad': 'TD',
            'Chile': 'CL',
            'China': 'CN',
            'Christmas Island': 'CX',
            'Cocos (Keeling) Islands': 'CC',
            'Colombia': 'CO',
            'Comoros': 'KM',
            'Congo': 'CG',
            'Congo, the Democratic Republic of the': 'CD',
            'Cook Islands': 'CK',
            'Costa Rica': 'CR',
            'Country name': 'Code',
            'Croatia': 'HR',
            'Cuba': 'CU',
            'Curaçao': 'CW',
            'Cyprus': 'CY',
            'Czech Republic': 'CZ',
            "Côte d'Ivoire": 'CI',
            'Denmark': 'DK',
            'Djibouti': 'DJ',
            'Dominica': 'DM',
            'Dominican Republic': 'DO',
            'Ecuador': 'EC',
            'Egypt': 'EG',
            'El Salvador': 'SV',
            'Equatorial Guinea': 'GQ',
            'Eritrea': 'ER',
            'Estonia': 'EE',
            'Ethiopia': 'ET',
            'Falkland Islands (Malvinas)': 'FK',
            'Faroe Islands': 'FO',
            'Fiji': 'FJ',
            'Finland': 'FI',
            'France': 'FR',
            'French Guiana': 'GF',
            'French Polynesia': 'PF',
            'French Southern Territories': 'TF',
            'Gabon': 'GA',
            'Gambia': 'GM',
            'Georgia': 'GE',
            'Germany': 'DE',
            'Ghana': 'GH',
            'Gibraltar': 'GI',
            'Greece': 'GR',
            'Greenland': 'GL',
            'Grenada': 'GD',
            'Guadeloupe': 'GP',
            'Guam': 'GU',
            'Guatemala': 'GT',
            'Guernsey': 'GG',
            'Guinea': 'GN',
            'Guinea-Bissau': 'GW',
            'Guyana': 'GY',
            'Haiti': 'HT',
            'Heard Island and McDonald Islands': 'HM',
            'Holy See (Vatican City State)': 'VA',
            'Honduras': 'HN',
            'Hong Kong': 'HK',
            'Hungary': 'HU',
            'ISO 3166-2:GB': '(.uk)',
            'Iceland': 'IS',
            'India': 'IN',
            'Indonesia': 'ID',
            'Iran, Islamic Republic of': 'IR',
            'Iraq': 'IQ',
            'Ireland': 'IE',
            'Isle of Man': 'IM',
            'Israel': 'IL',
            'Italy': 'IT',
            'Jamaica': 'JM',
            'Japan': 'JP',
            'Jersey': 'JE',
            'Jordan': 'JO',
            'Kazakhstan': 'KZ',
            'Kenya': 'KE',
            'Kiribati': 'KI',
            "Korea, Democratic People's Republic of": 'KP',
            'Korea, Republic of': 'KR',
            'Kuwait': 'KW',
            'Kyrgyzstan': 'KG',
            "Lao People's Democratic Republic": 'LA',
            'Latvia': 'LV',
            'Lebanon': 'LB',
            'Lesotho': 'LS',
            'Liberia': 'LR',
            'Libya': 'LY',
            'Liechtenstein': 'LI',
            'Lithuania': 'LT',
            'Luxembourg': 'LU',
            'Macao': 'MO',
            'Macedonia, the former Yugoslav Republic of': 'MK',
            'Madagascar': 'MG',
            'Malawi': 'MW',
            'Malaysia': 'MY',
            'Maldives': 'MV',
            'Mali': 'ML',
            'Malta': 'MT',
            'Marshall Islands': 'MH',
            'Martinique': 'MQ',
            'Mauritania': 'MR',
            'Mauritius': 'MU',
            'Mayotte': 'YT',
            'Mexico': 'MX',
            'Micronesia, Federated States of': 'FM',
            'Moldova, Republic of': 'MD',
            'Monaco': 'MC',
            'Mongolia': 'MN',
            'Montenegro': 'ME',
            'Montserrat': 'MS',
            'Morocco': 'MA',
            'Mozambique': 'MZ',
            'Myanmar': 'MM',
            'Namibia': 'NA',
            'Nauru': 'NR',
            'Nepal': 'NP',
            'Netherlands': 'NL',
            'New Caledonia': 'NC',
            'New Zealand': 'NZ',
            'Nicaragua': 'NI',
            'Niger': 'NE',
            'Nigeria': 'NG',
            'Niue': 'NU',
            'Norfolk Island': 'NF',
            'Northern Mariana Islands': 'MP',
            'Norway': 'NO',
            'Oman': 'OM',
            'Pakistan': 'PK',
            'Palau': 'PW',
            'Palestine, State of': 'PS',
            'Panama': 'PA',
            'Papua New Guinea': 'PG',
            'Paraguay': 'PY',
            'Peru': 'PE',
            'Philippines': 'PH',
            'Pitcairn': 'PN',
            'Poland': 'PL',
            'Portugal': 'PT',
            'Puerto Rico': 'PR',
            'Qatar': 'QA',
            'Romania': 'RO',
            'Russian Federation': 'RU',
            'Rwanda': 'RW',
            'Réunion': 'RE',
            'Saint Barthélemy': 'BL',
            'Saint Helena, Ascension and Tristan da Cunha': 'SH',
            'Saint Kitts and Nevis': 'KN',
            'Saint Lucia': 'LC',
            'Saint Martin (French part)': 'MF',
            'Saint Pierre and Miquelon': 'PM',
            'Saint Vincent and the Grenadines': 'VC',
            'Samoa': 'WS',
            'San Marino': 'SM',
            'Sao Tome and Principe': 'ST',
            'Saudi Arabia': 'SA',
            'Senegal': 'SN',
            'Serbia': 'RS',
            'Seychelles': 'SC',
            'Sierra Leone': 'SL',
            'Singapore': 'SG',
            'Sint Maarten (Dutch part)': 'SX',
            'Slovakia': 'SK',
            'Slovenia': 'SI',
            'Solomon Islands': 'SB',
            'Somalia': 'SO',
            'South Africa': 'ZA',
            'South Georgia and the South Sandwich Islands': 'GS',
            'South Sudan': 'SS',
            'Spain': 'ES',
            'Sri Lanka': 'LK',
            'Sudan': 'SD',
            'Suriname': 'SR',
            'Svalbard and Jan Mayen': 'SJ',
            'Swaziland': 'SZ',
            'Sweden': 'SE',
            'Switzerland': 'CH',
            'Syrian Arab Republic': 'SY',
            'Taiwan, Province of China': 'TW',
            'Tajikistan': 'TJ',
            'Tanzania, United Republic of': 'TZ',
            'Thailand': 'TH',
            'Timor-Leste': 'TL',
            'Togo': 'TG',
            'Tokelau': 'TK',
            'Tonga': 'TO',
            'Trinidad and Tobago': 'TT',
            'Tunisia': 'TN',
            'Turkey': 'TR',
            'Turkmenistan': 'TM',
            'Turks and Caicos Islands': 'TC',
            'Tuvalu': 'TV',
            'Uganda': 'UG',
            'Ukraine': 'UA',
            'United Arab Emirates': 'AE',
            'United Kingdom': 'GB',
            'United States': 'US',
            'United States Minor Outlying Islands': 'UM',
            'Uruguay': 'UY',
            'Uzbekistan': 'UZ',
            'Vanuatu': 'VU',
            'Venezuela, Bolivarian Republic of': 'VE',
            'Viet Nam': 'VN',
            'Virgin Islands, British': 'VG',
            'Virgin Islands, U.S.': 'VI',
            'Wallis and Futuna': 'WF',
            'Western Sahara': 'EH',
            'Yemen': 'YE',
            'Zambia': 'ZM',
            'Zimbabwe': 'ZW',
            'Åland Islands': 'AX'}

    async def _parse_data(self, data):
        celcius = data['main']['temp']-273
        fahrenheit = data['main']['temp']*9/5-459
        humidity = str(data['main']['humidity'])
        pressure = str(data['main']['pressure'])
        wind_kmh = str(round(data['wind']['speed'] * 3.6))
        wind_mph = str(round(data['wind']['speed'] * 2.23694))
        clouds = data['weather'][0]['description'].title()
        icon = data['weather'][0]['icon']
        place = data['name']
        country = [country for country, iso in self.countries.items() if iso == data['sys']['country']][0]
        city_id = data['id']
        parsed_data = collections.namedtuple('Parsed_data', 'celcius fahrenheit humidity pressure wind_kmh wind_mph clouds icon place country city_id')
        return parsed_data(celcius=celcius, fahrenheit=fahrenheit, humidity=humidity, pressure=pressure, wind_kmh=wind_kmh, wind_mph=wind_mph, clouds=clouds, icon=icon, place=place, country=country, city_id=city_id)

    async def _api_request(self, location):
        payload = {'q': location, 'appid': self.settings['WEATHER_API_KEY']}
        url = 'http://api.openweathermap.org/data/2.5/weather?'
        conn = aiohttp.TCPConnector()
        session = aiohttp.ClientSession(connector=conn)
        async with session.get(url, params=payload) as r:
            data = await r.json()
        session.close()
        return data

    @commands.command(pass_context=True, name='temperature', aliases=['temp'])
    async def _temperature(self, context, *, location: str):
        """Get the temperature only!"""
        if self.settings['WEATHER_API_KEY']:
            request = await self._api_request(location)
            if request['cod'] == 200:
                weather = await self._parse_data(request)
                message = '**{0.celcius:.1f} °C / {0.fahrenheit:.1f} °F in {0.place}, {0.country}**'.format(weather)
                await self.bot.say(message)
            else:
                await self.bot.say('Can\'t find this location!')
        else:
            message = 'No API key set. Get one at http://openweathermap.org/'
            await self.bot.say('```{}```'.format(message))

    @commands.command(pass_context=True, name='weather', aliases=['we'])
    async def _weather(self, context, *, location: str):
        """Get the weather!"""
        if self.settings['WEATHER_API_KEY']:
            request = await self._api_request(location)
            if request['cod'] == 200:
                weather = await self._parse_data(request)
                em = discord.Embed(title='{0.clouds} in {0.place}, {0.country}'.format(weather), color=discord.Color.blue(), description='\a\n', url='https://openweathermap.org/city/{0.city_id}'.format(weather))
                em.add_field(name='**Temperature**', value='{0.celcius:.1f} °C\n{0.fahrenheit:.1f} °F'.format(weather))
                em.add_field(name='**Wind**', value='{0.wind_kmh} km/h\n{0.wind_mph} mph'.format(weather))
                em.add_field(name='**Pressure / Humidity**', value='{0.pressure} hPa / {0.humidity}%'.format(weather))
                em.set_image(url='https://openweathermap.org/img/w/{}.png'.format(weather.icon))
                em.set_footer(text='Weather data provided by OpenWeatherMap', icon_url='http://openweathermap.org/themes/openweathermap/assets/vendor/owm/img/icons/logo_16x16.png')
                await self.bot.say(embed=em)
            else:
                await self.bot.say('Can\'t find this location!')
        else:
            message = 'No API key set. Get one at http://openweathermap.org/'
            await self.bot.say('```{}```'.format(message))

    @commands.command(pass_context=True, name='weatherkey')
    @checks.is_owner()
    async def _weatherkey(self, context, key: str):
        """Acquire a key from  http://openweathermap.org/"""
        settings = dataIO.load_json(self.settings_file)
        settings['WEATHER_API_KEY'] = key
        dataIO.save_json(self.settings_file, settings)
        await self.bot.say('Key saved! It might take a minute or ten before the key is active if you just registered it.')


def check_folder():
    if not os.path.exists("data/weather"):
        print("Creating data/weather folder...")
        os.makedirs("data/weather")


def check_file():
    weather = {}
    weather['WEATHER_API_KEY'] = False
    f = "data/weather/weather.json"
    if not dataIO.is_valid_json(f):
        print("Creating default weather.json...")
        dataIO.save_json(f, weather)


def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(Weather(bot))
