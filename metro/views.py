from decimal import Decimal
from collections import Counter, deque
import random

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Sum

from .models import Station, Ticket, MetroLine, StationFootfall, TransactionOTP

def get_shortest_path(start_station, end_station):
    if start_station == end_station:
        return 0, [], [start_station]

    queue = deque([start_station.id])
    visited = {start_station.id: None} 
    final_node_id = None

    while queue:
        current_id = queue.popleft()
        
        if current_id == end_station.id:
            final_node_id = current_id
            break

        current_stn = Station.objects.get(id=current_id)
        neighbors = []
        
        physical = Station.objects.filter(
            line=current_stn.line, 
            sequence_number__in=[current_stn.sequence_number - 1, current_stn.sequence_number + 1]
        )
        neighbors.extend(physical)
        
        transfers = Station.objects.filter(name__iexact=current_stn.name).exclude(id=current_id)
        neighbors.extend(transfers)

        for neighbor in neighbors:
            if neighbor.id not in visited:
                visited[neighbor.id] = current_stn
                queue.append(neighbor.id)

    if final_node_id is None:
        return None, [], []

    path_objs = []
    curr_id = final_node_id
    while curr_id is not None:
        stn = Station.objects.get(id=curr_id)
        path_objs.append(stn)
        parent = visited[curr_id]
        curr_id = parent.id if parent else None
    
    path_objs.reverse()
    
    instructions = []
    hops = 0
    for i in range(len(path_objs) - 1):
        curr = path_objs[i]
        next_stn = path_objs[i+1]
        
        if curr.name == next_stn.name and curr.line != next_stn.line:
            instructions.append(f"Switch at {curr.name} to {next_stn.line.name}")
        else:
            hops += 1
            
    return hops, instructions, path_objs

@login_required
def dashboard(request):
    if request.method == "POST" and 'add_funds' in request.POST:
        try:
            amount = Decimal(request.POST.get('amount'))
            if amount > 0:
                request.user.profile.balance += amount
                request.user.profile.save()
                messages.success(request, f"Successfully added ${amount} to your wallet!")
                return redirect('dashboard')
        except (ValueError, TypeError):
            messages.error(request, "Invalid amount entered.")

    tickets = Ticket.objects.filter(user=request.user).order_by('-purchase_time')
    return render(request, 'metro/dashboard.html', {'tickets': tickets})

@login_required
def metro_map(request):
    lines = MetroLine.objects.all()
    all_station_names = Station.objects.values_list('name', flat=True)
    name_counts = Counter(all_station_names)
    interchange_names = [name for name, count in name_counts.items() if count > 1]
    
    active_path_ids = []
    latest_ticket = Ticket.objects.filter(user=request.user).order_by('-purchase_time').first()
    
    route_info = "No recent ticket found."
    
    if latest_ticket:
        _, _, path_objs = get_shortest_path(latest_ticket.source, latest_ticket.destination)
        active_path_ids = [stn.id for stn in path_objs]
        route_info = f"Highlighting route: {latest_ticket.source.name} ➝ {latest_ticket.destination.name}"

    context = {
        'lines': lines,
        'interchange_names': interchange_names,
        'active_path_ids': active_path_ids,
        'route_info': route_info
    }
    return render(request, 'metro/map.html', context)

@login_required
def buy_ticket(request):
    stations = Station.objects.all().order_by('line__name', 'sequence_number')
    
    if request.method == 'POST':
        source_id = request.POST.get('source')
        dest_id = request.POST.get('destination')
        
        if source_id == dest_id:
            messages.error(request, "Source and Destination cannot be same.")
            return redirect('buy_ticket')

        source = Station.objects.get(id=source_id)
        dest = Station.objects.get(id=dest_id)
        
        hops, route_instructions, _ = get_shortest_path(source, dest)
        
        if hops is None:
            messages.error(request, "No route found!")
            return redirect('buy_ticket')
            
        price = hops * 10 
        
        if request.user.profile.balance < price:
            messages.error(request, "Insufficient Balance.")
            return redirect('dashboard') 
            
        otp_code = str(random.randint(100000, 999999))
        
        TransactionOTP.objects.create(
            user=request.user, otp_code=otp_code, source=source, destination=dest, price=price
        )
        
        send_mail(
            'Confirm Purchase',
            f'OTP: {otp_code}. Route: {" -> ".join(route_instructions)}',
            settings.DEFAULT_FROM_EMAIL,
            [request.user.email],
            fail_silently=False,
        )
        
        route_str = " -> ".join(route_instructions) if route_instructions else "Direct Route"
        messages.success(request, f"Route: {route_str}")
        messages.info(request, "OTP sent to your email.")
        return redirect('verify_otp')

    return render(request, 'metro/buy_ticket.html', {'stations': stations})

@login_required
def verify_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        try:
            txn = TransactionOTP.objects.filter(user=request.user).latest('created_at')
        except TransactionOTP.DoesNotExist:
            messages.error(request, "No pending transaction.")
            return redirect('buy_ticket')
            
        if txn.otp_code == entered_otp and txn.is_valid():
            if request.user.profile.balance < txn.price:
                messages.error(request, "Insufficient Balance.")
                return redirect('dashboard')

            request.user.profile.balance -= Decimal(txn.price)
            request.user.profile.save()
            
            Ticket.objects.create(
                user=request.user, source=txn.source, destination=txn.destination, price=txn.price
            )
            
            send_mail(
                'Ticket Confirmed',
                f'Ticket purchased for ${txn.price}.',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
                fail_silently=True,
            )

            txn.delete()
            messages.success(request, "Ticket Confirmed!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid or Expired OTP.")
    
    return render(request, 'metro/verify_otp.html')

@login_required
def scanner_view(request):
    if request.user.username != 'scanner':
        messages.error(request, "ACCESS DENIED: Restricted Area.")
        return redirect('dashboard')

    if request.method == 'POST':
        ticket_id = request.POST.get('ticket_id')
        action = request.POST.get('action') 
        
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            today = timezone.now().date()
            
            if action == 'entry':
                if ticket.status == 'ACTIVE':
                    ticket.status = 'IN_USE'
                    ticket.save()
                    log, _ = StationFootfall.objects.get_or_create(station=ticket.source, date=today)
                    log.entry_count += 1
                    log.save()
                    messages.success(request, f"Ticket #{ticket.id} Scanned IN at {ticket.source.name}")
                elif ticket.status == 'IN_USE':
                    messages.warning(request, f"ALREADY SCANNED IN!")
                else:
                    messages.error(request, f"Invalid Entry! Status is {ticket.status}")
            
            elif action == 'exit':
                if ticket.status == 'IN_USE':
                    ticket.status = 'USED'
                    ticket.save()
                    log, _ = StationFootfall.objects.get_or_create(station=ticket.destination, date=today)
                    log.exit_count += 1
                    log.save()
                    messages.success(request, f"Ticket #{ticket.id} Scanned OUT at {ticket.destination.name}")
                elif ticket.status == 'ACTIVE':
                    messages.error(request, "Ticket was never scanned at Entry!")
                else:
                    messages.error(request, f"Invalid Exit! Status is {ticket.status}")
                    
        except Ticket.DoesNotExist:
            messages.error(request, "Ticket not found.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            
    return render(request, 'metro/scanner.html')

@user_passes_test(lambda u: u.is_superuser)
def admin_stats(request):
    footfall = StationFootfall.objects.filter(date=timezone.now().date())
    return render(request, 'metro/admin_stats.html', {'footfall': footfall})


@login_required
def login_success(request):
    """
    Redirects users based on their role.
    """
    if request.user.username == 'scanner':
        return redirect('scanner') 
    elif request.user.is_superuser:
        return redirect('admin_stats') 
    else:
        return redirect('dashboard') 