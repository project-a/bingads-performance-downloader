# Changelog

## 2.3.0 (2019-02-25)

- Use BingAds API v12

**required changes** 

- Adapt ETL (read_csv.py) to new output column naming (GregorianDate renamed to TimePeriod)

## 2.2.0 - 2.2.1 (2018-05-23)

- Download campaign structure including labels on all levels as separate file
- Print Authorization Endpoint


**required changes** 

- Adapt ETL


## 2.1.0 (2018-03-27)

- Improve ordering of output columns (was quite random before)

**required changes** 

- Adapt ETL to new column order


## 2.0.0 (2018-03-14)

- Download both the keywords and the ad performance reports as two separate files (major version bump as the file name is different)



## 1.2.0 - 1.2.2 (2017-11-07)

- Use v11 reporting
- Fix check for existing files
- Cosmetic changes, upgrade bingads dependency

## 1.1.0 
*2017-09-21 

- Made the config and click commands discoverable in [mara-app](https://github.com/mara/mara-app) >= 1.2.0
- Documentation updates



