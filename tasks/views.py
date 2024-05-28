from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.db  import IntegrityError
from django.utils import timezone
from django.conf import settings


from .forms import TaskForm
from .models import Task

#Librearias de redes neurosales
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import load_model

#libreria de python
import numpy as np
import os


ruta_imagen = ""

# Create your views here.
def helloworld(request):
    return render(request, 'signup.html', {'form': UserCreationForm})

def home(request):
    return render(request, 'home.html')

def signup(request):
    
    if request.method == "GET":
        return render(request, 'signup.html', {'form': UserCreationForm})
    else:
        if request.POST['password1'] == request.POST['password2']:
            try:
                user = User.objects.create_user(username=request.POST['username'], password=request.POST['password1'])
                user.save()
                login(request, user)
                return redirect('tasks')
            except IntegrityError:
                return render(request, 'signup.html', {'form': UserCreationForm, 'error': 'Username already exists'})
        else:
            return render(request, 'signup.html', {'form': UserCreationForm, 'error': 'Password do not match'})

@login_required
def tasks(request):
    tasks = Task.objects.filter(user=request.user, datacompleted__isnull=True)
    return render(request, 'tasks.html', {'tasks': tasks})

@login_required
def tasks_complete(request):
    tasks = Task.objects.filter(user=request.user, datacompleted__isnull=False).order_by('-datacompleted')
    return render(request, 'tasks.html', {'tasks': tasks})

@login_required
def task_detail(request,task_id):
    if request.method == "GET":
        tasks = get_object_or_404(Task, pk=task_id, user=request.user)
        form = TaskForm(instance=tasks)
        return render(request, 'task_detail.html', {'task': tasks, 'form': form})
    else:
        try:
            task = get_object_or_404(Task, pk=task_id, user=request.user)
            form = TaskForm(request.POST, instance=task)
            form.save()
            return redirect('tasks')
        except ValueError:
            return render(request, 'task_detail.html', {'task': tasks, 'form': form ,'error': "Error updating task"})

@login_required
def complete_task(request,task_id):
    task = get_object_or_404(Task, pk=task_id, user=request.user)
    if request.method == "POST":
        task.datacompleted = timezone.now()
        task.save()
        return redirect('tasks')

@login_required    
def delete_task(request,task_id):
    task = get_object_or_404(Task, pk=task_id, user=request.user)
    if request.method == "POST":        
        task.delete()
        return redirect('tasks')

@login_required
def create_task(request):
    print("Entra")
    print(request.POST)
    if request.method =="POST":
        try:
            try:
                if 'title' in request.POST:
                    title = request.POST['title']
                else:
                    title = request.POST.get('title', ' ')

                if 'description' in request.POST:
                    description = request.POST['description']
                else:
                    description = request.POST.get('description', ' ')

                if 'important' in request.POST:
                    description = request.POST['important']
                else:
                    description = request.POST.get('important', ' ')

                # Carga de la imagen que deseas clasificar
                try:                   
                    images = request.FILES.get('image', None)
                    if images:
                        print(os.path.join(settings.MEDIA_ROOT, images.name))
                        # Guardar la imagen en una carpeta de tu proyecto
                        with open(os.path.join(settings.MEDIA_ROOT, images.name), 'wb+') as destination:
                            for chunk in images.chunks():
                                destination.write(chunk)
                        model_path_img = images.name                     
                    else:
                        return render(request, 'create_task.html', {'error': 'La imagen está vacía'})
                except ValueError:
                    return render(request, 'create_task.html', {'error': 'Seleccione una imagen'})             

            except ValueError:
                title = request.POST.get('title', ' ')
                description = request.POST.get('description', ' ')
                description = request.POST.get('important', ' ')

            #Cargamos las listas de pokemos
            model_path = os.path.join(settings.BASE_DIR, 'tasks', 'static', 'images')
            pokemon_names = sorted(os.listdir(model_path))

             # Carga del modelo desde el archivo pokemon.keras
            model_path = os.path.join(settings.BASE_DIR, 'tasks', 'models', 'model_pokemon.keras')
            model = load_model(model_path)
           
            # Carga de la imagen que deseas clasificar
            model_path = os.path.join(settings.BASE_DIR, 'tasks', 'static', 'prueba',model_path_img)  
            img = image.load_img(model_path, target_size=(150, 150))
  
            # Preprocesamiento de la imagen para que coincida con el formato de entrada del modelo
            img_array = image.img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)
            img_array /= 255.  # Normalización

            # Realizar la predicción
            prediction = model.predict(img_array)

            # Obtener la etiqueta de clase predicha
            predicted_class = np.argmax(prediction)

            # Mapear la etiqueta de clase a un nombre de Pokémon
            predicted_pokemon = pokemon_names[predicted_class]
            porcentaje_coincidencia = round(prediction[0][predicted_class] * 100, 2)

            print("El Pokémon en la imagen es:", predicted_pokemon)
            print("Porcentaje de coincidencia: {:.2f}%".format(porcentaje_coincidencia))
            if request.POST.get("important") == 'on':  
                form = TaskForm({
                    'title': predicted_pokemon,
                    'description': "Porcentaje de coincidencia: {:.2f}%".format(porcentaje_coincidencia),
                    'important': True
                })
                if form.is_valid():  # Verifica si el formulario es válido
                    new_task = form.save(commit=False)
                    new_task.user = request.user
                    new_task.save()
                    return redirect('tasks') 
                return render(request, 'create_task.html' , { 'error': 'No se pudo guardar correctamente',})        
            else:
                return render(request, 'create_task.html' , { 'form': TaskForm, 
                                                            'error': 'Guardado correctamente',
                                                            'description' : "Porcentaje de coincidencia: {:.2f}%".format(porcentaje_coincidencia),
                                                            'title' : predicted_pokemon})
        except ValueError:
            print(ValueError)
            return render(request, 'create_task.html' , { 'error': 'datos incorrectos', })
    else:
        return render(request, 'create_task.html' )

@login_required
def signout(request):
    logout(request)
    return redirect('home')

def signin(request):
    if request.method == 'GET':
        return render(request, 'signin.html',{'form': AuthenticationForm})
    else:
        user = authenticate(request, username=request.POST['username'], password=request.POST['password'] )
        if user is None:
            return render(request, 'signin.html',{'form': AuthenticationForm,'error': 'Username or password is incorrect'})
        else:
            login(request, user)
            return redirect('tasks')

def pokemon_list(request):
    # Obtener la ruta de la carpeta de imágenes de Pokémon
    pokemon_images_dir = os.path.join(settings.MEDIA_ROOT, 'pokemon_images')
    # Obtener una lista de nombres de las carpetas de Pokémon
    pokemon_folders = [name for name in os.listdir(pokemon_images_dir) if os.path.isdir(os.path.join(pokemon_images_dir, name))]
    return render(request, 'pokemon_list.html', {'pokemon_folders': pokemon_folders})

def pokemon_detail(request, pokemon_name):
    # Obtener la ruta de la carpeta de imágenes del Pokémon específico
    pokemon_folder_path = os.path.join(settings.MEDIA_ROOT, 'pokemon_images', pokemon_name)
    # Obtener una lista de nombres de archivos de imágenes en la carpeta del Pokémon
    pokemon_images = [name for name in os.listdir(pokemon_folder_path) if os.path.isfile(os.path.join(pokemon_folder_path, name))]
    return render(request, 'pokemon_detail.html', {'pokemon_name': pokemon_name, 'pokemon_images': pokemon_images})