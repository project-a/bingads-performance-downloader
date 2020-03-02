# Changelog

## 4.0.0 (2020-03-02)

- Changed the API so that it works with BingAds v13.
- Added scope to the report requests so that they can query the Bingads server.
- Removed language from the requests.
- Changed version number to 4.0.0 and the required bingads library to 13.0.1.

**required changes**

If used together with mara_app, then add the following lines to `local_setup.py`:

```
patch(bingads_downloader.config.oauth2_customer_id)(lambda: 2435435)
patch(bingads_downloader.config.oauth2_account_id)(lambda: 435435435)
patch(bingads_downloader.config.output_file_version)(lambda: 'v4')
patch(bingads_downloader.config.oauth2_account_array)(lambda: ['43543543','345435'])
```

A refresh of oauth2 Token needs to be run before running the downloads and updated.

## 3.0.0 (2019-04-12)

- Change MARA_XXX variables to functions to delay importing of imports

**required changes** 

- If used together with a mara project, Update `mara-app` to `>=2.0.0`


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



