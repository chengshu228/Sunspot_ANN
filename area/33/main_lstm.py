
import config
import ANN
import utils

import time
import os
import tensorflow as tf
gpus = tf.config.experimental.list_physical_devices('GPU')
tf.config.experimental.set_virtual_device_configuration(gpus[0],
    [tf.config.experimental.VirtualDeviceConfiguration(memory_limit=4608),
    tf.config.experimental.VirtualDeviceConfiguration(memory_limit=4608)])
import numpy as np
from tensorflow.keras import optimizers
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
import julian
import datetime
from matplotlib.font_manager import FontProperties

file_name = config.file_name
file_location = config.file_location
split_ratio = config.split_ratio
blocks = config.blocks
n_splits = config.n_splits
sun_epoch = config.sun_epoch
in_cycle = config.in_cycle
epochs = config.epochs
learning_rate = config.learning_rate
lat_sep = config.lat_sep
model_name = config.model_name

start_time = time.time()
np.random.seed(config.seed)
tf.random.set_seed(config.seed)

jul_date = np.loadtxt(file_location+r'\RGO_NOAA1874_2021\sa_train_jul_date.txt')
initial_julian = julian.to_jd(datetime.datetime(1870,1,1,0,0,0),fmt='jd')
end_julian = julian.to_jd(datetime.datetime(2030,1,1,0,0,0),fmt='jd')
x_jul, x_tick_time = [], []
for x_tick in np.arange(1870,2030+1,config.step): 
    t = datetime.datetime(x_tick,1,1,0,0,0)
    t_jd = julian.to_jd(t,fmt='jd')-initial_julian
    x_jul.append(t_jd)
    x_tick_time.append(x_tick)

sunspot = np.loadtxt(file_location+r'\RGO_NOAA1874_2021\sa_train.txt')
print(sunspot.shape)
input_data = np.array(sunspot[:,3:3+blocks*in_cycle*sun_epoch*12])
output_data = np.array(sunspot[:,3+blocks*in_cycle*sun_epoch*12:])      
print('\n\tinput_data=',input_data.shape,'output_data=',output_data.shape)

# from sklearn.decomposition import PCA
# n_components = 100
# pca = PCA(n_components=n_components)
# input_data = pca.fit_transform(input_data)
# print('\n\tinput_data=',input_data.shape,'output_data=',output_data.shape)

x_scaler = MinMaxScaler(feature_range=(0,1))
input_data = x_scaler.fit_transform(input_data)
y_scaler = MinMaxScaler(feature_range=(0,1)) 
output_data = y_scaler.fit_transform(output_data)

num1 = int(len(input_data)*split_ratio)
num2 = int(len(input_data)*(1-split_ratio)/2)
x_train, y_train = input_data[:num1,:], output_data[:num1,:]
x_val, y_val = input_data[num1:num1+num2,:], output_data[num1:num1+num2,:]
x_test, y_test = input_data[num1+num2:,:], output_data[num1+num2:,:]
x_train = np.expand_dims(x_train,axis=1)
x_val = np.expand_dims(x_val,axis=1)
x_test = np.expand_dims(x_test,axis=1)
print('\n\tshape: ', x_train.shape, y_train.shape,
    x_val.shape, y_val.shape, x_test.shape, y_test.shape)
val_loss_per_fold, val_mae_per_fold, val_rmse_per_fold = [], [], []

# model = ANN.cnn_lstm(x_train, output_node=output_data.shape[1], 
#         layer=config.layer, layer_size=config.layer_size, 
#         rate=config.rate, weight=config.weight)
model = ANN.stateless_lstm(x_train, output_node=output_data.shape[1], 
        layer=config.layer, layer_size=config.layer_size, 
        rate=config.rate, weight=config.weight)
print('\tmodel.summary(): \n{} '.format(model.summary()))
print('\tlayer nums:', len(model.layers))       

optimizer = optimizers.Adam(learning_rate=learning_rate) 
model.compile(optimizer=optimizer, loss='mean_squared_error',
    metrics=[tf.keras.metrics.RootMeanSquaredError(name='rmse')])
history = model.fit(x_train, y_train, verbose=2, epochs=epochs, 
    batch_size=len(x_train), validation_data=(x_val, y_val), 
    callbacks=utils.checkpoints(model_name, file_name), shuffle=False)    

model.save(file_location+r'\{}\{}.h5'.format(model_name, file_name))

train_loss, train_rmse = model.evaluate(x_train,y_train,verbose=2)
val_loss, val_rmse = model.evaluate(x_val,y_val,verbose=2)
test_loss, test_rmse = model.evaluate(x_test,y_test,verbose=2)
print('\tEvaluate on train set:MSE={0:.4f},RMSE={1:.4f}'.\
    format(train_loss, train_rmse))  
print('\tEvaluate on validation set:MSE={0:.4f},RMSE={1:.4f}'.\
    format(val_loss, val_rmse))  
print('\tEvaluate on test set:MSE={0:.4f},RMSE={1:.4f}'.\
    format(test_loss, test_rmse))        

val_loss_per_fold.append(val_loss)
val_rmse_per_fold.append(val_rmse)
test_loss_per_fold.append(test_loss)
test_rmse_per_fold.append(test_rmse)


y_train = y_scaler.inverse_transform(y_train)
y_train_pre = model.predict(x_train)
y_train_pre = y_scaler.inverse_transform(y_train_pre)
y_val = y_scaler.inverse_transform(y_val)
y_val_pre = model.predict(x_val)
y_val_pre = y_scaler.inverse_transform(y_val_pre)      

plt.figure(figsize=(10, 6))
plt.grid(True, linestyle='--', linewidth=1.0) 
for i in np.arange(blocks):
    if i==0:
        plt.scatter(jul_date[:num1, i], y_train[:, i],
            marker='o', c='grey', label='观测值', s=10)
        plt.scatter(jul_date[num1:, i], y_val[:, i], 
            marker='o', c='grey', s=10)
        plt.scatter(jul_date[:num1, i], y_train_pre[:, i],
            marker='+', c='dodgerblue', label=u'预测值 (训练集)', s=30)    
        plt.scatter(jul_date[num1:, i],  y_val_pre[:, i], 
            marker='x', c='darkviolet', label=u'预测值 (验证集)', s=25)
    else:
        plt.scatter(jul_date[:num1, i], y_train[:, i],
            marker='o', c='grey', s=10)
        plt.scatter(jul_date[num1:, i], y_val[:, i], 
            marker='o', c='grey', s=10)
        plt.scatter(jul_date[:num1, i], y_train_pre[:, i],
            marker='+', c='dodgerblue', s=30)    
        plt.scatter(jul_date[num1:, i], y_val_pre[:, i], 
            marker='x', c='darkviolet', s=25)
plt.xlabel(u'日期', fontproperties=fontcn, fontsize=18)         
plt.ylabel(u'月平均太阳黑子面积', fontproperties=fontcn, fontsize=18)  
plt.xlim(julian.to_jd(datetime.datetime(1870,1,1,0,0,0), fmt='jd')-initial_julian, 
    julian.to_jd(datetime.datetime(1990,1,1,0,0,0), fmt='jd')-initial_julian)
plt.xticks(x_jul, x_tick_time, size=14)
plt.yticks(size=14)
plt.legend(loc='best', prop=fontcn, fontsize=15) 
ax = plt.gca()
ax.spines['bottom'].set_linewidth(1.5)
ax.spines['left'].set_linewidth(1.5)
ax.spines['top'].set_linewidth(1.5)
ax.spines['right'].set_linewidth(1.5)
plt.tight_layout()
plt.show()

fig = plt.figure(figsize=(3.5, 3))  
plt.text(0.01, 0.85, 'Validation set Scores:', va='bottom', fontsize=14)
plt.text(0.01, 0.75, f' MSE:{np.mean(val_loss_per_fold):.4f}', va='bottom', fontsize=14)
plt.text(0.01, 0.65, f' MAE:{np.mean(val_mae_per_fold):.4f}(+/-{np.std(val_mae_per_fold):.4f})', 
    va='bottom', fontsize=14)
plt.text(0.01, 0.55, f' RMSE:{np.mean(val_rmse_per_fold):.4f}(+/-{np.std(val_rmse_per_fold):.4f})', 
    va='bottom', fontsize=14)
ax = plt.gca()
ax.axes.xaxis.set_ticks([])
ax.axes.yaxis.set_ticks([])
plt.tight_layout()
plt.show()

print((time.time()-start_time)/60, ' minutes')

# for i in np.arange(blocks):
#     plt.figure(figsize=(6, 5))
#     plt.grid(True, linestyle='--', linewidth=1.0) 
#     plt.scatter(jul_date[:num1][:,i], y_train[:,i],
#         marker='o', c='grey', label='Observed', s=10)
#     plt.scatter(jul_date[num1:num1+num2][:,i], y_val[:,i], 
#         marker='o', c='grey', s=10)
#     plt.scatter(jul_date[num1+num2:][:,i], y_test[:,i], 
#         marker='o', c='grey', s=10)
#     plt.scatter(jul_date[:num1][:,i], y_train_pre[:,i],
#         marker='+', c='dodgerblue', label='Predicted (Training Set)', s=30)    
#     plt.scatter(jul_date[num1:num1+num2][:,i], y_val_pre[:,i], 
#         marker='x', c='darkviolet', label='Predicted (Validation Set)', s=25)
#     plt.scatter(jul_date[num1+num2:][:,i], y_test_pre[:,i], 
#         marker='*', c='indianred', label='Predicted (Testing Set)', s=20)
#     # plt.title(f'All Set', fontproperties='Arial', fontsize=20, color='red')
#     plt.xlabel(label=u'日期', fontproperties=fontcn, fontsize=18)         
#     plt.ylabel(label=u'月平均太阳黑子面积', fontproperties=fontcn, fontsize=18)  
#     plt.xlim(julian.to_jd(datetime.datetime(1870,1,1,0,0,0), fmt='jd')-initial_julian, 
#         julian.to_jd(datetime.datetime(1990,1,1,0,0,0), fmt='jd')-initial_julian)
#     plt.xticks(x_jul, x_tick_time, size=14, rotation=45)
#     plt.yticks(size=14)
#     plt.legend(loc='upper left', prop=fonten, fontsize=12) 
#     ax = plt.gca()
#     ax.spines['bottom'].set_linewidth(1.5)
#     ax.spines['left'].set_linewidth(1.5)
#     ax.spines['top'].set_linewidth(1.5)
#     ax.spines['right'].set_linewidth(1.5)
#     plt.tight_layout()
#     plt.show()

# save_data(file_location=file_location+r'\loss', 
#     name='loss-{}-{}'.format(file_name, fold_no+1), value=history.history['loss'])    
# save_data(file_location=file_location+r'\loss', 
#     name='mae-{}-{}'.format(file_name, fold_no+1), value=history.history['mae'])    
# save_data(file_location=file_location+r'\loss', 
#     name='rmse-{}-{}'.format(file_name, fold_no+1), value=history.history['rmse'])  
# save_data(file_location=file_location+r'\loss', 
#     name='val_loss-{}-{}'.format(file_name, fold_no+1), value=history.history['val_loss'])    
# save_data(file_location=file_location+r'\loss', 
#     name='val_mae-{}-{}'.format(file_name, fold_no+1), value=history.history['val_mae'])    
# save_data(file_location=file_location+r'\loss', 
#     name='val_rmse-{}-{}'.format(file_name, fold_no+1), value=history.history['val_rmse'])  
