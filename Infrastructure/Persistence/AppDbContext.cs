using Microsoft.EntityFrameworkCore;
using Domain.Entities;

namespace Infrastructure.Persistence;

public class AppDbContext : DbContext
{

    public DbSet<DashboardAccount> DashboardAccounts { get; set; }
    public DbSet<Member>Members { get; set; }
    public DbSet<Registration_Request> Registration_Requests{ get; set; }
    public AppDbContext(DbContextOptions<AppDbContext> options): base(options)
    {

    }

 

  
}