## Oswa - inv


![OSWA-INV v2 image](https://scontent-iad3-1.xx.fbcdn.net/v/t31.0-8/12045296_896994067005023_5505146103193104549_o.jpg?oh=4afd029c1486604d29f672d76becb8bc&oe=5921F70A " Warehouse inventory system ")
#Warehouse inventory system
- - - -

The application was initially created by **Siamon Hasan**, useing [php](http:php.net), [mysql](https://www.mysql.com) and [bootstrap](http://getbootstrap.com).


OSWA-INV is a web based Inventory System, that will allow you to keep tracking of the quantity buying and selling price of the products existing in your warehouse or business. When creating a new products, you can set a quantity,buying and selling price.

****

If you find any bug, and a fix for that bug, please leave a comment on the github page for this project and i will push the change into the master branch.


### Installing this application is fairly easy, just follow these steps:
****


1. Download the latest version with git (`git clone https://github.com/siamon123/warehouse-inventory-system.git`)

2. Import/load oswa_inv.sql into your mysql database. This should set up the basic structure of the database system.

3. Set the database settings as environment variables of your web server / PHP process (nothing is stored in the code any more): `OSWA_DB_USER` and `OSWA_DB_PASS` are required, `OSWA_DB_HOST` (default `localhost`) and `OSWA_DB_NAME` (default `oswa_inv`) are optional. Example for a local test: `OSWA_DB_USER=myuser OSWA_DB_PASS=mypassword php -S 127.0.0.1:8080`. Without them the app stops with a clear "Configuration error" message.

4. Change all Folder permission inside uploads folder either add them to group call `www` if available or `777`.

5. Create the first administrator (there are no default accounts any more; the password must be at least 8 characters and is read from the environment, not the command line):

   `OSWA_NEW_PASSWORD='choose a long password' php bin/create_user.php admin "Your Name" 1`

   Levels: 1 = admin, 2 = special, 3 = user. Then log in with that **username** and **password**. Other users can be added from the "Add user" page.

6. Good luck!  

- - - -

## DON'T FORGET TO GIVE US FEEDBACK

- - - -

Like  [@OSWA](https://www.facebook.com/oswapp) on Facebook for more project.

Don't forget to visit [oswapp.com](http://oswapp.com "OSWA")
