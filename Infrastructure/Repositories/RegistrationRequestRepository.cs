using Domain.Entities;
using Domain.Interfaces;
using Infrastructure.Persistence;
using System;
using System.Collections.Generic;
using System.Text;

namespace Infrastructure.Repositories
{
    public class RegistrationRequestRepository: GenericRepository<Registration_Request>,IRegistrationRequestRepository
    {
        private readonly AppDbContext _context;

        public RegistrationRequestRepository(AppDbContext context)
            : base(context)
        {
            _context = context;
        }
    }
}
