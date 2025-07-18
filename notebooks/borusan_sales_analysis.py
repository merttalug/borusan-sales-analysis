# Databricks notebook source
from pyspark.sql.functions import col, round, avg

# JDBC bağlantı bilgileri
jdbcHostname = "borusansqlserver.database.windows.net"
jdbcDatabase = "borusansalesdb"
jdbcPort = 1433
jdbcUsername = "sqladmin"
jdbcPassword = "Grosso35"  # Gerekirse güncelle

# JDBC URL
jdbcUrl = f"jdbc:sqlserver://{jdbcHostname}:{jdbcPort};database={jdbcDatabase};encrypt=true"

# Bağlantı ayarları
connectionProperties = {
    "user": jdbcUsername,
    "password": jdbcPassword,
    "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver"
}

# SQL Server'dan satış verisini oku
sales_df = spark.read.jdbc(
    url=jdbcUrl,
    table="dbo.satislar",
    properties=connectionProperties
)

# Başarı oranı hesapla
sales_df = sales_df.withColumn(
    "satis_basarim_orani",
    round(col("satis_adedi") / col("hedef_satis"), 2)
)

# Kampanyalar tablosunu Hive üzerinden oku
kampanyalar_df = spark.table("kampanyalar").withColumnRenamed("Bayi Adı", "bayi_adi")

# Kampanya bilgisi ekle
kampanya_bayileri = kampanyalar_df.select("bayi_adi").distinct()
merged_df = sales_df.join(kampanya_bayileri, on="bayi_adi", how="left") \
    .withColumn("kampanya_var", col("bayi_adi").isin([row["bayi_adi"] for row in kampanya_bayileri.collect()]))

# Özet tablo: kampanyaya göre ortalama başarı oranı
kampanya_etki_df = merged_df.groupBy("kampanya_var") \
    .agg(avg("satis_basarim_orani").alias("ortalama_basarim_orani"))

# Databricks Unity Catalog kullanımı için veritabanı ve tabloyu tam nitelikli adla belirt
spark.sql("CREATE DATABASE IF NOT EXISTS spark_catalog.borusan_analiz")

# Detaylı veri tablosunu yaz
merged_df.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("spark_catalog.borusan_analiz.kampanya_etkisi")

# Özet tabloyu yaz
kampanya_etki_df.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("spark_catalog.borusan_analiz.kampanya_etki_ozeti")

